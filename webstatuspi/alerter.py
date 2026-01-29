"""Webhook and email alert system with state tracking and cooldown management."""

import logging
import smtplib
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from webstatuspi.config import AlertsConfig, SmtpConfig, UrlConfig, WebhookConfig
from webstatuspi.models import CheckResult
from webstatuspi.security import SSRFError, validate_url_for_ssrf

logger = logging.getLogger(__name__)


@dataclass
class StateTracker:
    """Track URL state changes and alert cooldowns."""

    last_state: dict[str, bool] = field(default_factory=dict)  # {url_name: is_up}
    last_alert_time: dict[str, float] = field(default_factory=dict)  # {url_name: timestamp}
    last_email_time: dict[str, float] = field(default_factory=dict)  # {url_name: timestamp}
    consecutive_slow: dict[str, int] = field(default_factory=dict)  # {url_name: count}
    is_latency_alert_active: dict[str, bool] = field(default_factory=dict)  # {url_name: bool}


class Alerter:
    """Manages webhook alerts with state tracking and delivery."""

    def __init__(self, config: AlertsConfig, max_retries: int = 3, retry_delay: int = 2):
        """Initialize alerter with configuration.

        Args:
            config: Alerts configuration with webhooks
            max_retries: Maximum number of retry attempts for failed webhooks
            retry_delay: Base delay in seconds between retries (increases exponentially)
        """
        self._config = config
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._state_tracker = StateTracker()
        self._lock = threading.Lock()

    def process_check_result(self, result: CheckResult) -> None:
        """Process a check result and send alerts if needed.

        Args:
            result: The check result to process
        """
        with self._lock:
            # Detect state change
            state_changed = self._should_alert(result)

            if state_changed:
                # Send alerts for all configured webhooks
                for webhook in self._config.webhooks:
                    if not webhook.enabled:
                        continue

                    # Check if this is the right event type
                    is_failure = not result.is_up
                    if is_failure and not webhook.on_failure:
                        continue
                    if not is_failure and not webhook.on_recovery:
                        continue

                    # Check cooldown
                    if not self._is_cooldown_expired(result.url_name, webhook.cooldown_seconds):
                        logger.debug(
                            "Webhook cooldown active for %s, skipping",
                            result.url_name,
                        )
                        continue

                    # Send webhook
                    self._send_webhook(webhook, result)

                # Send email alerts if SMTP is configured
                smtp = self._config.smtp
                if smtp and smtp.enabled:
                    is_failure = not result.is_up
                    if (is_failure and smtp.on_failure) or (not is_failure and smtp.on_recovery):
                        if self._is_email_cooldown_expired(result.url_name, smtp.cooldown_seconds):
                            self._send_email_alert(smtp, result)
                        else:
                            logger.debug(
                                "Email cooldown active for %s, skipping",
                                result.url_name,
                            )

            # Update state
            self._state_tracker.last_state[result.url_name] = result.is_up

    def check_latency_alert(
        self,
        url_config: UrlConfig,
        response_time_ms: int,
    ) -> None:
        """Check if latency alert should be triggered or cleared.

        Args:
            url_config: URL configuration with latency threshold settings.
            response_time_ms: Current response time in milliseconds.
        """
        if url_config.latency_threshold_ms is None:
            return

        with self._lock:
            threshold = url_config.latency_threshold_ms
            required = url_config.latency_consecutive_checks

            url_name = url_config.name
            consecutive_slow = self._state_tracker.consecutive_slow.get(url_name, 0)
            is_alert_active = self._state_tracker.is_latency_alert_active.get(url_name, False)

            if response_time_ms > threshold:
                consecutive_slow += 1
                self._state_tracker.consecutive_slow[url_name] = consecutive_slow

                # Trigger alert if threshold reached and not already active
                if consecutive_slow >= required and not is_alert_active:
                    self._state_tracker.is_latency_alert_active[url_name] = True
                    self._send_latency_webhook(url_config, response_time_ms, consecutive_slow, "latency_high")
            else:
                # Latency is normal - clear alert if active
                if is_alert_active:
                    self._state_tracker.is_latency_alert_active[url_name] = False
                    self._state_tracker.consecutive_slow[url_name] = 0
                    self._send_latency_webhook(url_config, response_time_ms, 0, "latency_normal")
                else:
                    # Reset counter if not in alert state
                    self._state_tracker.consecutive_slow[url_name] = 0

    def _should_alert(self, result: CheckResult) -> bool:
        """Check if we should send an alert for this result.

        Args:
            result: The check result

        Returns:
            True if the state changed, False otherwise
        """
        previous_state = self._state_tracker.last_state.get(result.url_name)

        # First check for a URL - always send alert
        if previous_state is None:
            return False

        # State change detected
        return previous_state != result.is_up

    def _is_cooldown_expired(self, url_name: str, cooldown_seconds: int) -> bool:
        """Check if cooldown period has expired.

        Args:
            url_name: Name of the URL
            cooldown_seconds: Cooldown period in seconds

        Returns:
            True if cooldown has expired or never set
        """
        last_alert = self._state_tracker.last_alert_time.get(url_name)
        if last_alert is None:
            return True

        elapsed = time.time() - last_alert
        return elapsed >= cooldown_seconds

    def _send_webhook(self, webhook: WebhookConfig, result: CheckResult) -> None:
        """Send a webhook alert (with retries).

        Args:
            webhook: The webhook configuration
            result: The check result that triggered the alert
        """
        # SSRF protection: validate webhook URL before sending
        try:
            validate_url_for_ssrf(webhook.url)
        except SSRFError as e:
            logger.error(
                "Webhook URL validation failed for %s: %s",
                webhook.url,
                e,
            )
            return

        payload = self._build_payload(result)
        retry_count = 0

        while retry_count <= self._max_retries:
            try:
                response = requests.post(
                    webhook.url,
                    json=payload,
                    timeout=10,
                )
                response.raise_for_status()

                logger.info(
                    "Webhook sent successfully for %s to %s",
                    result.url_name,
                    webhook.url,
                )
                self._state_tracker.last_alert_time[result.url_name] = time.time()
                return

            except requests.RequestException as e:
                retry_count += 1
                if retry_count <= self._max_retries:
                    delay = self._retry_delay * (2 ** (retry_count - 1))
                    logger.warning(
                        "Webhook failed for %s (attempt %d/%d, retrying in %ds): %s",
                        result.url_name,
                        retry_count,
                        self._max_retries + 1,
                        delay,
                        e,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Webhook failed for %s after %d attempts: %s",
                        result.url_name,
                        retry_count,
                        e,
                    )

    def _build_payload(self, result: CheckResult) -> dict:
        """Build the webhook payload.

        Args:
            result: The check result

        Returns:
            The webhook payload dictionary
        """
        previous_state = self._state_tracker.last_state.get(result.url_name)
        event_type = "url_down" if not result.is_up else "url_up"

        return {
            "event": event_type,
            "url": {
                "name": result.url_name,
                "url": result.url,
            },
            "status": {
                "code": result.status_code,
                "success": result.is_up,
                "response_time_ms": result.response_time_ms,
                "error": result.error_message,
                "timestamp": result.checked_at.isoformat(),
            },
            "previous_status": "up" if previous_state else "down" if previous_state is not None else None,
        }

    def _send_latency_webhook(
        self,
        url_config: UrlConfig,
        response_time_ms: int,
        consecutive_checks: int,
        event_type: str,
    ) -> None:
        """Send a latency alert webhook.

        Args:
            url_config: URL configuration with latency settings.
            response_time_ms: Current response time in milliseconds.
            consecutive_checks: Number of consecutive slow checks.
            event_type: Event type ("latency_high" or "latency_normal").
        """
        for webhook in self._config.webhooks:
            if not webhook.enabled:
                continue

            # Check cooldown
            if not self._is_cooldown_expired(url_config.name, webhook.cooldown_seconds):
                logger.debug(
                    "Webhook cooldown active for %s latency alert, skipping",
                    url_config.name,
                )
                continue

            # SSRF protection: validate webhook URL before sending
            try:
                validate_url_for_ssrf(webhook.url)
            except SSRFError as e:
                logger.error(
                    "Webhook URL validation failed for %s: %s",
                    webhook.url,
                    e,
                )
                continue

            payload = {
                "event": event_type,
                "url": {
                    "name": url_config.name,
                    "url": url_config.url,
                },
                "latency": {
                    "current_ms": response_time_ms,
                    "threshold_ms": url_config.latency_threshold_ms,
                    "consecutive_checks": consecutive_checks,
                },
                "timestamp": datetime.now(UTC).isoformat(),
            }

            retry_count = 0
            while retry_count <= self._max_retries:
                try:
                    response = requests.post(
                        webhook.url,
                        json=payload,
                        timeout=10,
                    )
                    response.raise_for_status()

                    logger.info(
                        "Latency webhook sent successfully for %s (%s) to %s",
                        url_config.name,
                        event_type,
                        webhook.url,
                    )
                    self._state_tracker.last_alert_time[url_config.name] = time.time()
                    return

                except requests.RequestException as e:
                    retry_count += 1
                    if retry_count <= self._max_retries:
                        delay = self._retry_delay * (2 ** (retry_count - 1))
                        logger.warning(
                            "Latency webhook failed for %s (attempt %d/%d, retrying in %ds): %s",
                            url_config.name,
                            retry_count,
                            self._max_retries + 1,
                            delay,
                            e,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "Latency webhook failed for %s after %d attempts: %s",
                            url_config.name,
                            retry_count,
                            e,
                        )

    def test_webhooks(self) -> dict[str, bool]:
        """Test all configured webhooks by sending a test payload.

        Returns:
            Dictionary mapping webhook URLs to success status
        """
        results = {}

        for webhook in self._config.webhooks:
            if not webhook.enabled:
                results[webhook.url] = False
                continue

            # SSRF protection: validate webhook URL before sending
            try:
                validate_url_for_ssrf(webhook.url)
            except SSRFError as e:
                logger.error(
                    "Webhook URL validation failed for %s: %s",
                    webhook.url,
                    e,
                )
                results[webhook.url] = False
                continue

            test_payload = {
                "event": "test",
                "url": {
                    "name": "TEST",
                    "url": "https://example.com",
                },
                "status": {
                    "code": 200,
                    "success": True,
                    "response_time_ms": 100,
                    "error": None,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                "previous_status": "up",
            }

            try:
                response = requests.post(
                    webhook.url,
                    json=test_payload,
                    timeout=10,
                )
                response.raise_for_status()
                results[webhook.url] = True
                logger.info("Test webhook sent successfully to %s", webhook.url)

            except requests.RequestException as e:
                results[webhook.url] = False
                logger.error("Test webhook failed for %s: %s", webhook.url, e)

        return results

    def _is_email_cooldown_expired(self, url_name: str, cooldown_seconds: int) -> bool:
        """Check if email cooldown period has expired.

        Args:
            url_name: Name of the URL
            cooldown_seconds: Cooldown period in seconds

        Returns:
            True if cooldown has expired or never set
        """
        last_email = self._state_tracker.last_email_time.get(url_name)
        if last_email is None:
            return True

        elapsed = time.time() - last_email
        return elapsed >= cooldown_seconds

    def _send_email_alert(self, smtp_config: SmtpConfig, result: CheckResult) -> None:
        """Send an email alert using SMTP.

        Args:
            smtp_config: SMTP configuration
            result: The check result that triggered the alert
        """
        subject, body_text, body_html = self._build_email_content(result)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_config.from_addr
        msg["To"] = ", ".join(smtp_config.to_addrs)

        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        retry_count = 0
        while retry_count <= self._max_retries:
            try:
                if smtp_config.use_tls:
                    server = smtplib.SMTP(smtp_config.host, smtp_config.port, timeout=30)
                    server.starttls()
                else:
                    server = smtplib.SMTP(smtp_config.host, smtp_config.port, timeout=30)

                if smtp_config.username and smtp_config.password:
                    server.login(smtp_config.username, smtp_config.password)

                server.sendmail(
                    smtp_config.from_addr,
                    smtp_config.to_addrs,
                    msg.as_string(),
                )
                server.quit()

                logger.info(
                    "Email alert sent successfully for %s to %s",
                    result.url_name,
                    ", ".join(smtp_config.to_addrs),
                )
                self._state_tracker.last_email_time[result.url_name] = time.time()
                return

            except (smtplib.SMTPException, OSError) as e:
                retry_count += 1
                if retry_count <= self._max_retries:
                    delay = self._retry_delay * (2 ** (retry_count - 1))
                    logger.warning(
                        "Email alert failed for %s (attempt %d/%d, retrying in %ds): %s",
                        result.url_name,
                        retry_count,
                        self._max_retries + 1,
                        delay,
                        e,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Email alert failed for %s after %d attempts: %s",
                        result.url_name,
                        retry_count,
                        e,
                    )

    def _build_email_content(self, result: CheckResult) -> tuple[str, str, str]:
        """Build email subject and body content.

        Args:
            result: The check result

        Returns:
            Tuple of (subject, plain_text_body, html_body)
        """
        previous_state = self._state_tracker.last_state.get(result.url_name)
        is_down = not result.is_up

        if is_down:
            status_emoji = "❌"
            status_text = "DOWN"
            status_color = "#dc3545"  # Red
        else:
            status_emoji = "✅"
            status_text = "UP"
            status_color = "#28a745"  # Green

        subject = f"{status_emoji} [{result.url_name}] Service is {status_text}"

        # Plain text body
        lines = [
            "WebStatusπ Alert",
            "",
            f"Service: {result.url_name}",
            f"URL: {result.url}",
            f"Status: {status_text}",
            f"Timestamp: {result.checked_at.isoformat()}",
        ]
        if result.status_code:
            lines.append(f"HTTP Status Code: {result.status_code}")
        if result.response_time_ms:
            lines.append(f"Response Time: {result.response_time_ms}ms")
        if result.error_message:
            lines.append(f"Error: {result.error_message}")
        if previous_state is not None:
            prev_status = "UP" if previous_state else "DOWN"
            lines.append(f"Previous Status: {prev_status}")
        body_text = "\n".join(lines)

        # HTML body
        html_parts = [
            f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: {status_color}; color: white; padding: 20px; border-radius: 8px; text-align: center;">
        <h1 style="margin: 0; font-size: 24px;">{status_emoji} Service is {status_text}</h1>
    </div>
    <div style="padding: 20px; background-color: #f8f9fa; border-radius: 8px; margin-top: 20px;">
        <h2 style="margin-top: 0; color: #333;">{result.url_name}</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #ddd; font-weight: bold;">URL</td>
                <td style="padding: 8px 0; border-bottom: 1px solid #ddd;"><a href="{result.url}">{result.url}</a></td>
            </tr>
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #ddd; font-weight: bold;">Status</td>
                <td style="padding: 8px 0; border-bottom: 1px solid #ddd; color: {status_color}; font-weight: bold;">{status_text}</td>
            </tr>"""
        ]

        if result.status_code:
            html_parts.append(f"""            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #ddd; font-weight: bold;">HTTP Code</td>
                <td style="padding: 8px 0; border-bottom: 1px solid #ddd;">{result.status_code}</td>
            </tr>""")

        if result.response_time_ms:
            html_parts.append(f"""            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #ddd; font-weight: bold;">Response Time</td>
                <td style="padding: 8px 0; border-bottom: 1px solid #ddd;">{result.response_time_ms}ms</td>
            </tr>""")

        if result.error_message:
            html_parts.append(f"""            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #ddd; font-weight: bold;">Error</td>
                <td style="padding: 8px 0; border-bottom: 1px solid #ddd; color: #dc3545;">{result.error_message}</td>
            </tr>""")

        html_parts.append(f"""            <tr>
                <td style="padding: 8px 0; font-weight: bold;">Timestamp</td>
                <td style="padding: 8px 0;">{result.checked_at.isoformat()}</td>
            </tr>
        </table>
    </div>
    <p style="color: #666; font-size: 12px; text-align: center; margin-top: 20px;">
        Sent by WebStatusπ
    </p>
</body>
</html>""")

        body_html = "\n".join(html_parts)

        return subject, body_text, body_html

    def test_smtp(self) -> bool:
        """Test SMTP configuration by sending a test email.

        Returns:
            True if test email was sent successfully, False otherwise
        """
        smtp_config = self._config.smtp
        if not smtp_config or not smtp_config.enabled:
            logger.warning("SMTP is not configured or not enabled")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "✅ WebStatusπ SMTP Test"
        msg["From"] = smtp_config.from_addr
        msg["To"] = ", ".join(smtp_config.to_addrs)

        body_text = (
            "This is a test email from WebStatusπ. If you received this, your SMTP configuration is working correctly."
        )
        body_html = """<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; padding: 20px;">
    <div style="background-color: #28a745; color: white; padding: 20px; border-radius: 8px; text-align: center;">
        <h1>✅ SMTP Test Successful</h1>
    </div>
    <p style="margin-top: 20px;">This is a test email from WebStatusπ. If you received this, your SMTP configuration is working correctly.</p>
</body>
</html>"""

        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        try:
            if smtp_config.use_tls:
                server = smtplib.SMTP(smtp_config.host, smtp_config.port, timeout=30)
                server.starttls()
            else:
                server = smtplib.SMTP(smtp_config.host, smtp_config.port, timeout=30)

            if smtp_config.username and smtp_config.password:
                server.login(smtp_config.username, smtp_config.password)

            server.sendmail(
                smtp_config.from_addr,
                smtp_config.to_addrs,
                msg.as_string(),
            )
            server.quit()

            logger.info("Test email sent successfully to %s", ", ".join(smtp_config.to_addrs))
            return True

        except (smtplib.SMTPException, OSError) as e:
            logger.error("Test email failed: %s", e)
            return False
