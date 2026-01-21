"""Tests for the webhook alerter module."""

import json
from datetime import datetime
from typing import Dict
from unittest.mock import MagicMock, Mock, patch

import pytest

from webstatuspi.alerter import Alerter, StateTracker
from webstatuspi.config import AlertsConfig, WebhookConfig
from webstatuspi.models import CheckResult


class TestStateTracker:
    """Tests for the StateTracker class."""

    def test_initialization(self) -> None:
        """Test state tracker initialization."""
        tracker = StateTracker()
        assert tracker.last_state == {}
        assert tracker.last_alert_time == {}

    def test_track_state(self) -> None:
        """Test tracking URL state."""
        tracker = StateTracker()
        tracker.last_state["test_url"] = True
        assert tracker.last_state["test_url"] is True

    def test_track_alert_time(self) -> None:
        """Test tracking alert times."""
        tracker = StateTracker()
        import time
        current_time = time.time()
        tracker.last_alert_time["test_url"] = current_time
        assert tracker.last_alert_time["test_url"] == current_time


class TestAlerter:
    """Tests for the Alerter class."""

    @pytest.fixture
    def webhook_config(self) -> AlertsConfig:
        """Create test webhook configuration."""
        webhook = WebhookConfig(
            url="https://example.com/webhook",
            enabled=True,
            on_failure=True,
            on_recovery=True,
            cooldown_seconds=300,
        )
        return AlertsConfig(webhooks=[webhook])

    @pytest.fixture
    def alerter(self, webhook_config: AlertsConfig) -> Alerter:
        """Create test alerter instance."""
        return Alerter(webhook_config, max_retries=2, retry_delay=1)

    @pytest.fixture
    def check_result_up(self) -> CheckResult:
        """Create a successful check result."""
        return CheckResult(
            url_name="test_url",
            url="https://example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=datetime.utcnow(),
        )

    @pytest.fixture
    def check_result_down(self) -> CheckResult:
        """Create a failed check result."""
        return CheckResult(
            url_name="test_url",
            url="https://example.com",
            status_code=503,
            response_time_ms=5000,
            is_up=False,
            error_message="Service Unavailable",
            checked_at=datetime.utcnow(),
        )

    def test_initialization(self, alerter: Alerter) -> None:
        """Test alerter initialization."""
        assert len(alerter._config.webhooks) == 1
        assert alerter._max_retries == 2
        assert alerter._retry_delay == 1

    def test_first_check_no_alert(
        self, alerter: Alerter, check_result_down: CheckResult
    ) -> None:
        """Test that first check doesn't trigger alert (no state change)."""
        with patch.object(alerter, "_send_webhook") as mock_send:
            alerter.process_check_result(check_result_down)
            # First check should not send alert
            mock_send.assert_not_called()

    def test_state_change_down_triggers_alert(
        self, alerter: Alerter, check_result_up: CheckResult, check_result_down: CheckResult
    ) -> None:
        """Test that state change from UP to DOWN triggers alert."""
        # Set initial state to UP
        alerter._state_tracker.last_state["test_url"] = True

        with patch.object(alerter, "_send_webhook") as mock_send:
            alerter.process_check_result(check_result_down)
            mock_send.assert_called_once()

    def test_state_change_up_triggers_alert(
        self, alerter: Alerter, check_result_up: CheckResult, check_result_down: CheckResult
    ) -> None:
        """Test that state change from DOWN to UP triggers alert."""
        # Set initial state to DOWN
        alerter._state_tracker.last_state["test_url"] = False

        with patch.object(alerter, "_send_webhook") as mock_send:
            alerter.process_check_result(check_result_up)
            mock_send.assert_called_once()

    def test_no_state_change_no_alert(
        self, alerter: Alerter, check_result_up: CheckResult
    ) -> None:
        """Test that no alert is sent when state doesn't change."""
        # Set initial state to UP
        alerter._state_tracker.last_state["test_url"] = True

        with patch.object(alerter, "_send_webhook") as mock_send:
            alerter.process_check_result(check_result_up)
            mock_send.assert_not_called()

    def test_on_failure_filter(
        self, check_result_down: CheckResult
    ) -> None:
        """Test that on_failure filter works."""
        webhook = WebhookConfig(
            url="https://example.com/webhook",
            enabled=True,
            on_failure=False,  # Don't send on failure
            on_recovery=True,
        )
        alerter = Alerter(AlertsConfig(webhooks=[webhook]))
        alerter._state_tracker.last_state["test_url"] = True

        with patch.object(alerter, "_send_webhook") as mock_send:
            alerter.process_check_result(check_result_down)
            mock_send.assert_not_called()

    def test_on_recovery_filter(
        self, check_result_up: CheckResult
    ) -> None:
        """Test that on_recovery filter works."""
        webhook = WebhookConfig(
            url="https://example.com/webhook",
            enabled=True,
            on_failure=True,
            on_recovery=False,  # Don't send on recovery
        )
        alerter = Alerter(AlertsConfig(webhooks=[webhook]))
        alerter._state_tracker.last_state["test_url"] = False

        with patch.object(alerter, "_send_webhook") as mock_send:
            alerter.process_check_result(check_result_up)
            mock_send.assert_not_called()

    def test_disabled_webhook_not_sent(
        self, check_result_down: CheckResult
    ) -> None:
        """Test that disabled webhooks are not sent."""
        webhook = WebhookConfig(
            url="https://example.com/webhook",
            enabled=False,  # Disabled
            on_failure=True,
            on_recovery=True,
        )
        alerter = Alerter(AlertsConfig(webhooks=[webhook]))
        alerter._state_tracker.last_state["test_url"] = True

        with patch.object(alerter, "_send_webhook") as mock_send:
            alerter.process_check_result(check_result_down)
            mock_send.assert_not_called()

    def test_cooldown_prevents_alert(
        self, alerter: Alerter, check_result_down: CheckResult, check_result_up: CheckResult
    ) -> None:
        """Test that cooldown prevents duplicate alerts."""
        alerter._state_tracker.last_state["test_url"] = True
        import time
        alerter._state_tracker.last_alert_time["test_url"] = time.time()

        with patch.object(alerter, "_send_webhook") as mock_send:
            alerter.process_check_result(check_result_down)
            mock_send.assert_not_called()

    def test_cooldown_expiration_allows_alert(
        self, alerter: Alerter, check_result_down: CheckResult
    ) -> None:
        """Test that alert is sent after cooldown expires."""
        alerter._state_tracker.last_state["test_url"] = True
        alerter._state_tracker.last_alert_time["test_url"] = 0  # Very old timestamp

        with patch.object(alerter, "_send_webhook") as mock_send:
            alerter.process_check_result(check_result_down)
            mock_send.assert_called_once()

    def test_build_payload(
        self, alerter: Alerter, check_result_down: CheckResult
    ) -> None:
        """Test webhook payload structure."""
        alerter._state_tracker.last_state["test_url"] = True

        payload = alerter._build_payload(check_result_down)

        assert payload["event"] == "url_down"
        assert payload["url"]["name"] == "test_url"
        assert payload["url"]["url"] == "https://example.com"
        assert payload["status"]["code"] == 503
        assert payload["status"]["success"] is False
        assert payload["status"]["response_time_ms"] == 5000
        assert payload["status"]["error"] == "Service Unavailable"
        assert payload["previous_status"] == "up"

    def test_build_payload_up_event(
        self, alerter: Alerter, check_result_up: CheckResult
    ) -> None:
        """Test webhook payload for UP event."""
        alerter._state_tracker.last_state["test_url"] = False

        payload = alerter._build_payload(check_result_up)

        assert payload["event"] == "url_up"
        assert payload["status"]["success"] is True
        assert payload["previous_status"] == "down"

    @patch("webstatuspi.alerter.requests.post")
    def test_send_webhook_success(
        self, mock_post: Mock, alerter: Alerter, check_result_down: CheckResult
    ) -> None:
        """Test successful webhook delivery."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        webhook = alerter._config.webhooks[0]
        alerter._send_webhook(webhook, check_result_down)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://example.com/webhook"
        assert kwargs["timeout"] == 10
        assert isinstance(kwargs["json"], dict)
        assert "event" in kwargs["json"]

    @patch("webstatuspi.alerter.requests.post")
    def test_send_webhook_retry_on_failure(
        self, mock_post: Mock, check_result_down: CheckResult
    ) -> None:
        """Test that webhook retries on failure."""
        import requests
        mock_post.side_effect = requests.RequestException("Connection error")

        webhook = WebhookConfig(
            url="https://example.com/webhook",
            enabled=True,
            on_failure=True,
            on_recovery=True,
            cooldown_seconds=0,
        )
        alerter = Alerter(AlertsConfig(webhooks=[webhook]), max_retries=2, retry_delay=0)

        alerter._send_webhook(webhook, check_result_down)

        # Should attempt 3 times (initial + 2 retries)
        assert mock_post.call_count == 3

    @patch("webstatuspi.alerter.requests.post")
    def test_send_webhook_success_after_retry(
        self, mock_post: Mock, check_result_down: CheckResult
    ) -> None:
        """Test successful delivery after retry."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None

        import requests
        # Fail first, succeed second
        mock_post.side_effect = [
            requests.RequestException("Connection error"),
            mock_response,
        ]

        webhook = WebhookConfig(
            url="https://example.com/webhook",
            enabled=True,
            on_failure=True,
            on_recovery=True,
            cooldown_seconds=0,
        )
        alerter = Alerter(AlertsConfig(webhooks=[webhook]), max_retries=2, retry_delay=0)

        alerter._send_webhook(webhook, check_result_down)

        # Should succeed after retry
        assert mock_post.call_count == 2

    @patch("webstatuspi.alerter.requests.post")
    def test_test_webhooks_all_success(
        self, mock_post: Mock, alerter: Alerter
    ) -> None:
        """Test successful webhook testing."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        results = alerter.test_webhooks()

        assert results["https://example.com/webhook"] is True
        mock_post.assert_called_once()

    @patch("webstatuspi.alerter.requests.post")
    def test_test_webhooks_failure(
        self, mock_post: Mock, alerter: Alerter
    ) -> None:
        """Test failed webhook testing."""
        import requests
        mock_post.side_effect = requests.RequestException("Connection error")

        results = alerter.test_webhooks()

        assert results["https://example.com/webhook"] is False

    def test_test_webhooks_disabled_webhook(self) -> None:
        """Test that disabled webhooks are skipped in test."""
        webhook = WebhookConfig(
            url="https://example.com/webhook",
            enabled=False,
        )
        alerter = Alerter(AlertsConfig(webhooks=[webhook]))

        with patch("webstatuspi.alerter.requests.post") as mock_post:
            results = alerter.test_webhooks()
            assert results["https://example.com/webhook"] is False
            mock_post.assert_not_called()

    def test_multiple_webhooks(self) -> None:
        """Test alerter with multiple webhooks."""
        webhooks = [
            WebhookConfig(url="https://example.com/webhook1", enabled=True),
            WebhookConfig(url="https://example.com/webhook2", enabled=True),
            WebhookConfig(url="https://example.com/webhook3", enabled=False),
        ]
        alerter = Alerter(AlertsConfig(webhooks=webhooks))

        assert len(alerter._config.webhooks) == 3

    def test_thread_safety_lock(self, alerter: Alerter) -> None:
        """Test that lock attribute exists for thread safety."""
        import threading
        # Verify lock exists and has acquire/release methods (duck typing)
        assert hasattr(alerter, "_lock")
        assert hasattr(alerter._lock, "acquire")
        assert hasattr(alerter._lock, "release")
        assert callable(alerter._lock.acquire)
        assert callable(alerter._lock.release)
