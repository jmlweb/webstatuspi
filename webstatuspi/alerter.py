"""Webhook alert system with state tracking and cooldown management."""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

import requests

from webstatuspi.config import AlertsConfig, WebhookConfig
from webstatuspi.models import CheckResult
from webstatuspi.security import SSRFError, validate_url_for_ssrf

logger = logging.getLogger(__name__)


@dataclass
class StateTracker:
    """Track URL state changes and alert cooldowns."""

    last_state: dict[str, bool] = field(default_factory=dict)  # {url_name: is_up}
    last_alert_time: dict[str, float] = field(default_factory=dict)  # {url_name: timestamp}


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
