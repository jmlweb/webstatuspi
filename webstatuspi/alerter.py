"""Webhook alert system with state tracking and cooldown management."""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

import requests

from webstatuspi.config import AlertsConfig, UrlConfig, WebhookConfig
from webstatuspi.models import CheckResult
from webstatuspi.security import SSRFError, validate_url_for_ssrf

logger = logging.getLogger(__name__)


@dataclass
class StateTracker:
    """Track URL state changes and alert cooldowns."""

    last_state: dict[str, bool] = field(default_factory=dict)  # {url_name: is_up}
    last_alert_time: dict[str, float] = field(default_factory=dict)  # {url_name: timestamp}
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
