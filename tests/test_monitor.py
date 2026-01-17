"""Tests for the monitor module."""

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from webstatuspi.config import Config, DatabaseConfig, MonitorConfig, UrlConfig
from webstatuspi.database import init_db
from webstatuspi.models import CheckResult
from webstatuspi.monitor import MAX_WORKERS, Monitor, check_url


@pytest.fixture
def db_conn(tmp_path: Path) -> sqlite3.Connection:
    """Create a database connection with initialized tables."""
    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    yield conn
    conn.close()


@pytest.fixture
def url_config() -> UrlConfig:
    """Create a sample URL configuration."""
    return UrlConfig(
        name="TEST",
        url="https://httpbin.org/status/200",
        timeout=5,
    )


@pytest.fixture
def config() -> Config:
    """Create a sample configuration with multiple URLs."""
    return Config(
        urls=[
            UrlConfig(name="URL_A", url="https://example.com", timeout=5),
            UrlConfig(name="URL_B", url="https://example.org", timeout=5),
        ],
        monitor=MonitorConfig(interval=60),
        database=DatabaseConfig(path="./test.db", retention_days=7),
    )


class TestCheckUrl:
    """Tests for check_url function."""

    def test_returns_check_result(self, url_config: UrlConfig) -> None:
        """Returns a CheckResult instance."""
        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert isinstance(result, CheckResult)
            assert result.url_name == "TEST"
            assert result.url == "https://httpbin.org/status/200"

    def test_successful_check_is_up(self, url_config: UrlConfig) -> None:
        """Successful 2xx response marks URL as up."""
        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is True
            assert result.status_code == 200
            assert result.error_message is None

    def test_redirect_is_up(self, url_config: UrlConfig) -> None:
        """3xx redirect responses mark URL as up."""
        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 301
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is True
            assert result.status_code == 301

    @pytest.mark.parametrize("redirect_code", [301, 302, 303, 307, 308])
    def test_all_redirect_codes_are_up(
        self, url_config: UrlConfig, redirect_code: int
    ) -> None:
        """All 3xx redirect codes are treated as up."""
        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = redirect_code
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is True, f"Redirect {redirect_code} should be up"
            assert result.status_code == redirect_code

    def test_redirect_followed_returns_final_status(
        self, url_config: UrlConfig
    ) -> None:
        """When redirect is followed, final status code is returned.

        urllib.request.urlopen follows redirects by default,
        so the final status (e.g., 200) is what we receive.
        """
        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            # Simulate urllib following redirect and returning final 200
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is True
            assert result.status_code == 200

    def test_redirect_does_not_cause_exception(self, url_config: UrlConfig) -> None:
        """Redirects don't raise exceptions or cause failures."""
        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            # Simulate redirect being followed successfully
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.error_message is None
            assert result.is_up is True

    @pytest.mark.parametrize("redirect_code", [301, 302, 303, 307, 308])
    def test_redirect_as_http_error_is_up(
        self, url_config: UrlConfig, redirect_code: int
    ) -> None:
        """Redirects raised as HTTPError are still treated as up.

        Some redirect codes (especially 308) may be raised as HTTPError
        instead of being followed automatically by urllib.
        """
        import urllib.error

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url_config.url, redirect_code, "Redirect", {}, None
            )

            result = check_url(url_config)

            assert result.is_up is True, f"Redirect {redirect_code} as HTTPError should be up"
            assert result.status_code == redirect_code
            assert result.error_message is None

    def test_client_error_is_down(self, url_config: UrlConfig) -> None:
        """4xx client error marks URL as down."""
        import urllib.error

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url_config.url, 404, "Not Found", {}, None
            )

            result = check_url(url_config)

            assert result.is_up is False
            assert result.status_code == 404
            assert "404" in result.error_message

    def test_server_error_is_down(self, url_config: UrlConfig) -> None:
        """5xx server error marks URL as down."""
        import urllib.error

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url_config.url, 500, "Internal Server Error", {}, None
            )

            result = check_url(url_config)

            assert result.is_up is False
            assert result.status_code == 500
            assert "500" in result.error_message

    def test_connection_error_is_down(self, url_config: UrlConfig) -> None:
        """Connection errors mark URL as down with no status code."""
        import urllib.error

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

            result = check_url(url_config)

            assert result.is_up is False
            assert result.status_code is None
            assert result.error_message is not None

    def test_timeout_is_down(self, url_config: UrlConfig) -> None:
        """Timeout errors mark URL as down."""
        import socket

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_urlopen.side_effect = socket.timeout("timed out")

            result = check_url(url_config)

            assert result.is_up is False
            assert result.status_code is None

    def test_measures_response_time(self, url_config: UrlConfig) -> None:
        """Response time is measured in milliseconds."""
        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert isinstance(result.response_time_ms, int)
            assert result.response_time_ms >= 0

    def test_sets_checked_at_timestamp(self, url_config: UrlConfig) -> None:
        """Checked at timestamp is set to current time."""
        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            before = datetime.utcnow()
            result = check_url(url_config)
            after = datetime.utcnow()

            assert before <= result.checked_at <= after


class TestMonitor:
    """Tests for Monitor class."""

    def test_init_creates_staggered_schedule(
        self, config: Config, db_conn: sqlite3.Connection
    ) -> None:
        """Initial check times are staggered to avoid burst."""
        monitor = Monitor(config, db_conn)

        # Check that URLs have different scheduled times
        times = list(monitor._next_check.values())
        assert len(times) == 2
        assert times[1] > times[0]  # Second URL scheduled later

    def test_start_begins_monitoring(
        self, config: Config, db_conn: sqlite3.Connection
    ) -> None:
        """Start method begins the monitor loop."""
        monitor = Monitor(config, db_conn)
        monitor.start()

        try:
            assert monitor.is_running()
        finally:
            monitor.stop()

    def test_stop_halts_monitoring(
        self, config: Config, db_conn: sqlite3.Connection
    ) -> None:
        """Stop method halts the monitor loop."""
        monitor = Monitor(config, db_conn)
        monitor.start()
        monitor.stop(timeout=5.0)

        assert not monitor.is_running()

    def test_multiple_start_calls_safe(
        self, config: Config, db_conn: sqlite3.Connection
    ) -> None:
        """Multiple start calls don't create multiple threads."""
        monitor = Monitor(config, db_conn)
        monitor.start()
        monitor.start()  # Second call should be ignored

        try:
            assert monitor.is_running()
        finally:
            monitor.stop()

    def test_stop_on_non_running_safe(
        self, config: Config, db_conn: sqlite3.Connection
    ) -> None:
        """Stop on non-running monitor doesn't error."""
        monitor = Monitor(config, db_conn)
        monitor.stop()  # Should not raise

    def test_on_check_callback_invoked(
        self, config: Config, db_conn: sqlite3.Connection
    ) -> None:
        """on_check callback is invoked for each check."""
        results: List[CheckResult] = []

        def callback(result: CheckResult) -> None:
            results.append(result)

        # Create config with immediate checks
        quick_config = Config(
            urls=[UrlConfig(name="QUICK", url="https://example.com", timeout=2)],
            monitor=MonitorConfig(interval=1),
            database=config.database,
        )

        with patch("webstatuspi.monitor.check_url") as mock_check:
            mock_check.return_value = CheckResult(
                url_name="QUICK",
                url="https://example.com",
                status_code=200,
                response_time_ms=50,
                is_up=True,
                error_message=None,
                checked_at=datetime.utcnow(),
            )

            monitor = Monitor(quick_config, db_conn, on_check=callback)
            # Manually trigger a check cycle
            monitor._next_check["QUICK"] = 0  # Make it due immediately
            monitor._check_urls(quick_config.urls)

            assert len(results) == 1
            assert results[0].url_name == "QUICK"

    def test_stores_results_in_database(
        self, config: Config, db_conn: sqlite3.Connection
    ) -> None:
        """Check results are stored in database."""
        with patch("webstatuspi.monitor.check_url") as mock_check:
            mock_check.return_value = CheckResult(
                url_name="URL_A",
                url="https://example.com",
                status_code=200,
                response_time_ms=50,
                is_up=True,
                error_message=None,
                checked_at=datetime.utcnow(),
            )

            monitor = Monitor(config, db_conn)
            monitor._next_check["URL_A"] = 0

            # Check just URL_A
            url_a = config.urls[0]
            monitor._check_urls([url_a])

            # Verify stored in DB
            cursor = db_conn.execute("SELECT * FROM checks WHERE url_name = ?", ("URL_A",))
            row = cursor.fetchone()

            assert row is not None
            assert row["url_name"] == "URL_A"
            assert row["status_code"] == 200

    def test_handles_check_failure_gracefully(
        self, config: Config, db_conn: sqlite3.Connection
    ) -> None:
        """Check failures don't stop the monitor."""
        with patch("webstatuspi.monitor.check_url") as mock_check:
            mock_check.side_effect = Exception("Unexpected error")

            monitor = Monitor(config, db_conn)
            monitor._next_check["URL_A"] = 0

            # Should not raise
            url_a = config.urls[0]
            monitor._check_urls([url_a])

            # Next check should still be scheduled
            assert monitor._next_check["URL_A"] > 0

    def test_get_urls_due_returns_due_urls(
        self, config: Config, db_conn: sqlite3.Connection
    ) -> None:
        """_get_urls_due returns URLs that are due for checking."""
        monitor = Monitor(config, db_conn)
        now = time.monotonic()

        # Set one URL as due, one as not due
        monitor._next_check["URL_A"] = now - 10  # Past due
        monitor._next_check["URL_B"] = now + 100  # Not due yet

        due = monitor._get_urls_due(now)

        assert len(due) == 1
        assert due[0].name == "URL_A"


class TestMonitorCleanup:
    """Tests for Monitor cleanup functionality."""

    def test_cleanup_runs_periodically(
        self, config: Config, db_conn: sqlite3.Connection
    ) -> None:
        """Cleanup runs after CLEANUP_INTERVAL_CYCLES cycles."""
        from webstatuspi.monitor import CLEANUP_INTERVAL_CYCLES

        with patch("webstatuspi.monitor.cleanup_old_checks") as mock_cleanup:
            mock_cleanup.return_value = 0

            monitor = Monitor(config, db_conn)
            monitor._cycle_count = CLEANUP_INTERVAL_CYCLES - 1

            # Simulate a check cycle completing
            with patch("webstatuspi.monitor.check_url") as mock_check:
                mock_check.return_value = CheckResult(
                    url_name="URL_A",
                    url="https://example.com",
                    status_code=200,
                    response_time_ms=50,
                    is_up=True,
                    error_message=None,
                    checked_at=datetime.utcnow(),
                )

                monitor._next_check["URL_A"] = 0
                monitor._check_urls([config.urls[0]])
                monitor._cycle_count += 1

                # Now run cleanup check
                if monitor._cycle_count >= CLEANUP_INTERVAL_CYCLES:
                    monitor._run_cleanup()
                    mock_cleanup.assert_called_once()

    def test_cleanup_uses_retention_days_from_config(
        self, config: Config, db_conn: sqlite3.Connection
    ) -> None:
        """Cleanup uses retention_days from config."""
        with patch("webstatuspi.monitor.cleanup_old_checks") as mock_cleanup:
            mock_cleanup.return_value = 5

            monitor = Monitor(config, db_conn)
            monitor._run_cleanup()

            mock_cleanup.assert_called_once_with(db_conn, 7)  # retention_days=7


class TestMaxWorkers:
    """Tests for thread pool configuration."""

    def test_max_workers_is_reasonable(self) -> None:
        """MAX_WORKERS is set to a reasonable value for Pi 1B+."""
        assert MAX_WORKERS >= 2
        assert MAX_WORKERS <= 5
