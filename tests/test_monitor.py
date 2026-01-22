"""Tests for the monitor module."""

import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from webstatuspi.config import Config, DatabaseConfig, MonitorConfig, TcpConfig, UrlConfig
from webstatuspi.database import init_db
from webstatuspi.models import CheckResult
from webstatuspi.monitor import (
    MAX_WORKERS,
    Monitor,
    SSLCertInfo,
    _get_ssl_cert_info,
    _is_success_status,
    check_tcp,
    check_url,
)


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
    def test_all_redirect_codes_are_up(self, url_config: UrlConfig, redirect_code: int) -> None:
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

    def test_redirect_followed_returns_final_status(self, url_config: UrlConfig) -> None:
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
    def test_redirect_as_http_error_is_up(self, url_config: UrlConfig, redirect_code: int) -> None:
        """Redirects raised as HTTPError are still treated as up.

        Some redirect codes (especially 308) may be raised as HTTPError
        instead of being followed automatically by urllib.
        """
        import urllib.error

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(url_config.url, redirect_code, "Redirect", {}, None)

            result = check_url(url_config)

            assert result.is_up is True, f"Redirect {redirect_code} as HTTPError should be up"
            assert result.status_code == redirect_code
            assert result.error_message is None

    def test_client_error_is_down(self, url_config: UrlConfig) -> None:
        """4xx client error marks URL as down."""
        import urllib.error

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(url_config.url, 404, "Not Found", {}, None)

            result = check_url(url_config)

            assert result.is_up is False
            assert result.status_code == 404
            assert "404" in result.error_message

    def test_server_error_is_down(self, url_config: UrlConfig) -> None:
        """5xx server error marks URL as down."""
        import urllib.error

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(url_config.url, 500, "Internal Server Error", {}, None)

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

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("timed out")

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

            before = datetime.now(UTC)
            result = check_url(url_config)
            after = datetime.now(UTC)

            assert before <= result.checked_at <= after

    def test_captures_content_length_from_response(self, url_config: UrlConfig) -> None:
        """Content-Length header is captured from HTTP response."""
        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {"Content-Length": "1024"}
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.content_length == 1024

    def test_content_length_none_when_header_missing(self, url_config: UrlConfig) -> None:
        """Content-Length is None when header not present in response."""
        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.content_length is None

    def test_captures_content_length_from_http_error(self, url_config: UrlConfig) -> None:
        """Content-Length is captured from HTTPError responses."""
        import urllib.error
        from unittest.mock import Mock

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_headers = Mock()
            mock_headers.get = MagicMock(return_value="512")
            mock_error = urllib.error.HTTPError(
                url_config.url,
                404,
                "Not Found",
                mock_headers,  # type: ignore[arg-type]
                None,
            )
            mock_urlopen.side_effect = mock_error

            result = check_url(url_config)

            assert result.content_length == 512

    def test_content_length_none_for_http_error_without_header(self, url_config: UrlConfig) -> None:
        """Content-Length is None for HTTPError without the header."""
        import urllib.error
        from unittest.mock import Mock

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_headers = Mock()
            mock_headers.get = MagicMock(return_value=None)
            mock_error = urllib.error.HTTPError(
                url_config.url,
                500,
                "Internal Server Error",
                mock_headers,  # type: ignore[arg-type]
                None,
            )
            mock_urlopen.side_effect = mock_error

            result = check_url(url_config)

            assert result.content_length is None

    def test_content_length_none_for_connection_errors(self, url_config: UrlConfig) -> None:
        """Content-Length is None for connection errors."""
        import urllib.error

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

            result = check_url(url_config)

            assert result.content_length is None

    def test_captures_server_header_from_response(self, url_config: UrlConfig) -> None:
        """Server header is captured from HTTP response."""
        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {"Server": "nginx/1.18.0"}
            mock_response.reason = "OK"
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.server_header == "nginx/1.18.0"

    def test_server_header_none_when_header_missing(self, url_config: UrlConfig) -> None:
        """Server header is None when not present in response."""
        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.reason = "OK"
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.server_header is None

    def test_captures_status_text_from_response(self, url_config: UrlConfig) -> None:
        """Status text (reason phrase) is captured from HTTP response."""
        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.reason = "OK"
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.status_text == "OK"

    def test_status_text_captured_for_error_responses(self, url_config: UrlConfig) -> None:
        """Status text is captured for error responses."""
        import urllib.error

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_error = urllib.error.HTTPError(
                url_config.url,
                404,
                "Not Found",
                {},
                None,
            )
            mock_urlopen.side_effect = mock_error

            result = check_url(url_config)

            assert result.status_text == "Not Found"

    def test_captures_server_header_from_http_error(self, url_config: UrlConfig) -> None:
        """Server header is captured from HTTPError responses."""
        import urllib.error
        from unittest.mock import Mock

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_headers = Mock()
            mock_headers.get = MagicMock(side_effect=lambda key: "Apache/2.4.41" if key == "Server" else None)
            mock_error = urllib.error.HTTPError(
                url_config.url,
                500,
                "Internal Server Error",
                mock_headers,  # type: ignore[arg-type]
                None,
            )
            mock_urlopen.side_effect = mock_error

            result = check_url(url_config)

            assert result.server_header == "Apache/2.4.41"

    def test_server_header_none_for_http_error_without_header(self, url_config: UrlConfig) -> None:
        """Server header is None for HTTPError without the header."""
        import urllib.error
        from unittest.mock import Mock

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_headers = Mock()
            mock_headers.get = MagicMock(return_value=None)
            mock_error = urllib.error.HTTPError(
                url_config.url,
                503,
                "Service Unavailable",
                mock_headers,  # type: ignore[arg-type]
                None,
            )
            mock_urlopen.side_effect = mock_error

            result = check_url(url_config)

            assert result.server_header is None

    def test_server_header_none_for_connection_errors(self, url_config: UrlConfig) -> None:
        """Server header is None for connection errors."""
        import urllib.error

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

            result = check_url(url_config)

            assert result.server_header is None

    def test_status_text_none_for_connection_errors(self, url_config: UrlConfig) -> None:
        """Status text is None for connection errors."""
        import urllib.error

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

            result = check_url(url_config)

            assert result.status_text is None

    @pytest.mark.parametrize(
        "server_value",
        [
            "nginx/1.18.0",
            "Apache/2.4.41 (Ubuntu)",
            "cloudflare",
            "Microsoft-IIS/10.0",
        ],
    )
    def test_various_server_header_values(self, url_config: UrlConfig, server_value: str) -> None:
        """Different server header values are captured correctly."""
        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {"Server": server_value}
            mock_response.reason = "OK"
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.server_header == server_value


class TestMonitor:
    """Tests for Monitor class."""

    def test_init_creates_staggered_schedule(self, config: Config, db_conn: sqlite3.Connection) -> None:
        """Initial check times are staggered to avoid burst."""
        monitor = Monitor(config, db_conn)

        # Check that URLs have different scheduled times
        times = list(monitor._next_check.values())
        assert len(times) == 2
        assert times[1] > times[0]  # Second URL scheduled later

    def test_start_begins_monitoring(self, config: Config, db_conn: sqlite3.Connection) -> None:
        """Start method begins the monitor loop."""
        monitor = Monitor(config, db_conn)
        monitor.start()

        try:
            assert monitor.is_running()
        finally:
            monitor.stop()

    def test_stop_halts_monitoring(self, config: Config, db_conn: sqlite3.Connection) -> None:
        """Stop method halts the monitor loop."""
        monitor = Monitor(config, db_conn)
        monitor.start()
        monitor.stop(timeout=5.0)

        assert not monitor.is_running()

    def test_multiple_start_calls_safe(self, config: Config, db_conn: sqlite3.Connection) -> None:
        """Multiple start calls don't create multiple threads."""
        monitor = Monitor(config, db_conn)
        monitor.start()
        monitor.start()  # Second call should be ignored

        try:
            assert monitor.is_running()
        finally:
            monitor.stop()

    def test_stop_on_non_running_safe(self, config: Config, db_conn: sqlite3.Connection) -> None:
        """Stop on non-running monitor doesn't error."""
        monitor = Monitor(config, db_conn)
        monitor.stop()  # Should not raise

    def test_on_check_callback_invoked(self, config: Config, db_conn: sqlite3.Connection) -> None:
        """on_check callback is invoked for each check."""
        results: list[CheckResult] = []

        def callback(result: CheckResult) -> None:
            results.append(result)

        # Create config with minimum allowed interval
        quick_config = Config(
            urls=[UrlConfig(name="QUICK", url="https://example.com", timeout=2)],
            monitor=MonitorConfig(interval=10),
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
                checked_at=datetime.now(UTC),
            )

            monitor = Monitor(quick_config, db_conn, on_check=callback)
            # Manually trigger a check cycle
            monitor._next_check["QUICK"] = 0  # Make it due immediately
            monitor._check_urls(quick_config.urls)

            assert len(results) == 1
            assert results[0].url_name == "QUICK"

    def test_stores_results_in_database(self, config: Config, db_conn: sqlite3.Connection) -> None:
        """Check results are stored in database."""
        with patch("webstatuspi.monitor.check_url") as mock_check:
            mock_check.return_value = CheckResult(
                url_name="URL_A",
                url="https://example.com",
                status_code=200,
                response_time_ms=50,
                is_up=True,
                error_message=None,
                checked_at=datetime.now(UTC),
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

    def test_handles_check_failure_gracefully(self, config: Config, db_conn: sqlite3.Connection) -> None:
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

    def test_get_urls_due_returns_due_urls(self, config: Config, db_conn: sqlite3.Connection) -> None:
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

    def test_cleanup_runs_periodically(self, config: Config, db_conn: sqlite3.Connection) -> None:
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
                    checked_at=datetime.now(UTC),
                )

                monitor._next_check["URL_A"] = 0
                monitor._check_urls([config.urls[0]])
                monitor._cycle_count += 1

                # Now run cleanup check
                if monitor._cycle_count >= CLEANUP_INTERVAL_CYCLES:
                    monitor._run_cleanup()
                    mock_cleanup.assert_called_once()

    def test_cleanup_uses_retention_days_from_config(self, config: Config, db_conn: sqlite3.Connection) -> None:
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


class TestContentValidation:
    """Tests for content validation (keyword and JSON path)."""

    def test_keyword_validation_success(self) -> None:
        """Keyword validation passes when keyword is found in response body."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com",
            timeout=5,
            keyword="OK",
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.read = MagicMock(return_value=b"Status: OK")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is True
            assert result.error_message is None

    def test_keyword_validation_failure(self) -> None:
        """Keyword validation fails when keyword is not found in response body."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com",
            timeout=5,
            keyword="SUCCESS",
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.read = MagicMock(return_value=b"Status: ERROR")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is False
            assert result.status_code == 200  # HTTP request succeeded
            assert "not found" in result.error_message

    def test_keyword_validation_case_sensitive(self) -> None:
        """Keyword validation is case-sensitive."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com",
            timeout=5,
            keyword="OK",
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.read = MagicMock(return_value=b"Status: ok")  # lowercase
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is False
            assert "not found" in result.error_message

    def test_json_path_validation_success(self) -> None:
        """JSON path validation passes when path exists with truthy value."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com/api/health",
            timeout=5,
            json_path="status.healthy",
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.read = MagicMock(return_value=b'{"status": {"healthy": true}}')
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is True
            assert result.error_message is None

    def test_json_path_validation_success_with_string_value(self) -> None:
        """JSON path validation passes with truthy string value."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com/api/health",
            timeout=5,
            json_path="status",
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.read = MagicMock(return_value=b'{"status": "ok"}')
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is True
            assert result.error_message is None

    def test_json_path_validation_failure_missing_path(self) -> None:
        """JSON path validation fails when path does not exist."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com/api/health",
            timeout=5,
            json_path="status.healthy",
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.read = MagicMock(return_value=b'{"status": {}}')
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is False
            assert "not found" in result.error_message
            assert "healthy" in result.error_message

    def test_json_path_validation_failure_falsy_value(self) -> None:
        """JSON path validation fails when value is falsy."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com/api/health",
            timeout=5,
            json_path="status.healthy",
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.read = MagicMock(return_value=b'{"status": {"healthy": false}}')
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is False
            assert "falsy value" in result.error_message

    def test_json_path_validation_failure_invalid_json(self) -> None:
        """JSON path validation fails when response is not valid JSON."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com/api/health",
            timeout=5,
            json_path="status",
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.read = MagicMock(return_value=b"Not JSON")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is False
            assert "invalid JSON" in result.error_message

    def test_validation_skipped_when_http_error(self) -> None:
        """Content validation is skipped when HTTP request fails."""
        import urllib.error

        url_config = UrlConfig(
            name="TEST",
            url="https://example.com",
            timeout=5,
            keyword="OK",
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url_config.url,
                500,
                "Internal Server Error",
                {},
                None,
            )

            result = check_url(url_config)

            assert result.is_up is False
            assert result.status_code == 500
            assert "500" in result.error_message
            assert "keyword" not in result.error_message.lower()

    def test_validation_handles_non_utf8_response(self) -> None:
        """Content validation fails gracefully with non-UTF-8 response."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com",
            timeout=5,
            keyword="OK",
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.read = MagicMock(return_value=b"\xff\xfe\xfd")  # Invalid UTF-8
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is False
            assert "UTF-8" in result.error_message

    def test_validation_limits_body_size(self) -> None:
        """Content validation limits response body to MAX_BODY_SIZE."""
        from webstatuspi.monitor import MAX_BODY_SIZE

        url_config = UrlConfig(
            name="TEST",
            url="https://example.com",
            timeout=5,
            keyword="OK",
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            # Create large response body
            large_body = b"x" * (MAX_BODY_SIZE + 1000) + b"OK"
            mock_response.read = MagicMock(return_value=large_body[:MAX_BODY_SIZE])
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            check_url(url_config)

            # Verify read was called with MAX_BODY_SIZE limit
            mock_response.read.assert_called_once_with(MAX_BODY_SIZE)

    def test_no_validation_when_not_configured(self) -> None:
        """No validation is performed when keyword and json_path are not set."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com",
            timeout=5,
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is True
            assert result.error_message is None
            # Verify read was not called
            mock_response.read.assert_not_called()


class TestIsSuccessStatus:
    """Tests for _is_success_status function."""

    def test_default_accepts_2xx(self) -> None:
        """Default behavior accepts 2xx status codes."""
        assert _is_success_status(200, None) is True
        assert _is_success_status(201, None) is True
        assert _is_success_status(299, None) is True

    def test_default_accepts_3xx(self) -> None:
        """Default behavior accepts 3xx status codes."""
        assert _is_success_status(300, None) is True
        assert _is_success_status(301, None) is True
        assert _is_success_status(399, None) is True

    def test_default_rejects_4xx(self) -> None:
        """Default behavior rejects 4xx status codes."""
        assert _is_success_status(400, None) is False
        assert _is_success_status(404, None) is False
        assert _is_success_status(499, None) is False

    def test_default_rejects_5xx(self) -> None:
        """Default behavior rejects 5xx status codes."""
        assert _is_success_status(500, None) is False
        assert _is_success_status(503, None) is False
        assert _is_success_status(599, None) is False

    def test_custom_single_codes(self) -> None:
        """Custom single codes work correctly."""
        codes = [200, 201, 202]
        assert _is_success_status(200, codes) is True
        assert _is_success_status(201, codes) is True
        assert _is_success_status(202, codes) is True
        assert _is_success_status(203, codes) is False
        assert _is_success_status(301, codes) is False

    def test_custom_range_codes(self) -> None:
        """Custom range codes work correctly."""
        codes: list[int | tuple[int, int]] = [(200, 299)]
        assert _is_success_status(200, codes) is True
        assert _is_success_status(250, codes) is True
        assert _is_success_status(299, codes) is True
        assert _is_success_status(199, codes) is False
        assert _is_success_status(300, codes) is False

    def test_custom_mixed_codes(self) -> None:
        """Custom mixed single codes and ranges work correctly."""
        codes: list[int | tuple[int, int]] = [(200, 299), 400]
        assert _is_success_status(200, codes) is True
        assert _is_success_status(250, codes) is True
        assert _is_success_status(299, codes) is True
        assert _is_success_status(400, codes) is True  # Special case
        assert _is_success_status(401, codes) is False
        assert _is_success_status(500, codes) is False

    def test_empty_list_rejects_all(self) -> None:
        """Empty list rejects all status codes."""
        assert _is_success_status(200, []) is False
        assert _is_success_status(404, []) is False


class TestCustomSuccessCodesInCheckUrl:
    """Tests for custom success codes in check_url."""

    def test_custom_codes_accept_configured_status(self) -> None:
        """Custom success codes accept configured status codes."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com",
            timeout=5,
            success_codes=[200, 201, 400],  # 400 is success for this API
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 400  # Normally a failure
            mock_response.headers = {}
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is True
            assert result.status_code == 400

    def test_custom_codes_reject_non_configured_status(self) -> None:
        """Custom success codes reject non-configured status codes."""
        import urllib.error

        url_config = UrlConfig(
            name="TEST",
            url="https://example.com",
            timeout=5,
            success_codes=[200, 201],  # Only 200 and 201
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url_config.url,
                301,  # Normally a success (redirect)
                "Moved Permanently",
                {},
                None,
            )

            result = check_url(url_config)

            assert result.is_up is False
            assert result.status_code == 301

    def test_custom_range_accepts_status_in_range(self) -> None:
        """Custom range accepts status codes within the range."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com",
            timeout=5,
            success_codes=[(200, 299), (400, 401)],
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 250
            mock_response.headers = {}
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is True
            assert result.status_code == 250

    def test_no_custom_codes_uses_default(self) -> None:
        """No custom codes uses default behavior (200-399)."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com",
            timeout=5,
            # No success_codes specified
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 301
            mock_response.headers = {}
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config)

            assert result.is_up is True  # Default includes 3xx


class TestCheckTcp:
    """Tests for check_tcp function."""

    def test_successful_tcp_connection(self) -> None:
        """Successful TCP connection marks target as up."""
        tcp_config = TcpConfig(
            name="TCP_TEST",
            host="example.com",
            port=80,
            timeout=5,
        )

        with patch("webstatuspi.monitor.socket.create_connection") as mock_conn:
            mock_sock = MagicMock()
            mock_conn.return_value = mock_sock

            result = check_tcp(tcp_config)

            assert result.is_up is True
            assert result.url_name == "TCP_TEST"
            assert result.url == "tcp://example.com:80"
            assert result.status_code is None
            assert result.error_message is None
            mock_sock.close.assert_called_once()

    def test_tcp_connection_timeout(self) -> None:
        """TCP connection timeout marks target as down."""

        tcp_config = TcpConfig(
            name="TCP_TEST",
            host="example.com",
            port=80,
            timeout=5,
        )

        with patch("webstatuspi.monitor.socket.create_connection") as mock_conn:
            mock_conn.side_effect = TimeoutError("timed out")

            result = check_tcp(tcp_config)

            assert result.is_up is False
            assert result.url_name == "TCP_TEST"
            assert "timeout" in result.error_message.lower()

    def test_tcp_connection_refused(self) -> None:
        """TCP connection refused marks target as down."""
        tcp_config = TcpConfig(
            name="TCP_TEST",
            host="example.com",
            port=80,
            timeout=5,
        )

        with patch("webstatuspi.monitor.socket.create_connection") as mock_conn:
            mock_conn.side_effect = OSError("Connection refused")

            result = check_tcp(tcp_config)

            assert result.is_up is False
            assert result.url_name == "TCP_TEST"
            assert "refused" in result.error_message.lower()

    def test_tcp_measures_response_time(self) -> None:
        """TCP check measures connection time in milliseconds."""
        tcp_config = TcpConfig(
            name="TCP_TEST",
            host="example.com",
            port=80,
            timeout=5,
        )

        with patch("webstatuspi.monitor.socket.create_connection") as mock_conn:
            mock_sock = MagicMock()
            mock_conn.return_value = mock_sock

            result = check_tcp(tcp_config)

            assert isinstance(result.response_time_ms, int)
            assert result.response_time_ms >= 0

    def test_tcp_sets_checked_at_timestamp(self) -> None:
        """TCP check sets checked_at timestamp."""
        tcp_config = TcpConfig(
            name="TCP_TEST",
            host="example.com",
            port=80,
            timeout=5,
        )

        with patch("webstatuspi.monitor.socket.create_connection") as mock_conn:
            mock_sock = MagicMock()
            mock_conn.return_value = mock_sock

            before = datetime.now(UTC)
            result = check_tcp(tcp_config)
            after = datetime.now(UTC)

            assert before <= result.checked_at <= after


class TestSSLCertExtraction:
    """Tests for SSL certificate extraction functionality."""

    def test_http_url_returns_none(self) -> None:
        """HTTP URLs return None for SSL cert info (no SSL)."""
        ssl_info, error = _get_ssl_cert_info("http://example.com", timeout=5)

        assert ssl_info is None
        assert error is None

    def test_https_url_extracts_cert_info(self) -> None:
        """HTTPS URLs return SSL cert info when successful."""
        # Mock the SSL connection
        mock_cert = {
            "subject": ((("commonName", "example.com"),),),
            "issuer": ((("organizationName", "Let's Encrypt"),),),
            "notAfter": "Dec 31 23:59:59 2025 GMT",
        }

        with patch("webstatuspi.monitor.socket.create_connection") as mock_conn:
            mock_ssl_sock = MagicMock()
            mock_ssl_sock.getpeercert.return_value = mock_cert
            mock_ssl_sock.__enter__ = MagicMock(return_value=mock_ssl_sock)
            mock_ssl_sock.__exit__ = MagicMock(return_value=False)

            mock_sock = MagicMock()
            mock_sock.__enter__ = MagicMock(return_value=mock_sock)
            mock_sock.__exit__ = MagicMock(return_value=False)
            mock_conn.return_value = mock_sock

            with patch("webstatuspi.monitor.ssl.create_default_context") as mock_ctx:
                mock_context = MagicMock()
                mock_context.wrap_socket.return_value = mock_ssl_sock
                mock_ctx.return_value = mock_context

                ssl_info, error = _get_ssl_cert_info("https://example.com", timeout=5)

        assert error is None
        assert ssl_info is not None
        assert ssl_info.issuer == "Let's Encrypt"
        assert ssl_info.subject == "example.com"
        assert ssl_info.expires_at is not None

    def test_ssl_connection_failure_returns_error(self) -> None:
        """SSL connection failures return error message."""
        import ssl

        with patch("webstatuspi.monitor.socket.create_connection") as mock_conn:
            mock_conn.side_effect = ssl.SSLError("Connection refused")

            ssl_info, error = _get_ssl_cert_info("https://example.com", timeout=5)

        assert ssl_info is None
        assert "SSL error" in error

    def test_ssl_timeout_returns_error(self) -> None:
        """SSL connection timeout returns error message."""
        with patch("webstatuspi.monitor.socket.create_connection") as mock_conn:
            mock_conn.side_effect = TimeoutError("timed out")

            ssl_info, error = _get_ssl_cert_info("https://example.com", timeout=5)

        assert ssl_info is None
        assert "timeout" in error.lower()

    def test_invalid_hostname_returns_error(self) -> None:
        """Invalid hostname returns error message."""
        ssl_info, error = _get_ssl_cert_info("https://", timeout=5)

        assert ssl_info is None
        assert "hostname" in error.lower() or "invalid" in error.lower()


class TestSSLCertInCheckUrl:
    """Tests for SSL certificate integration in check_url."""

    def test_ssl_fields_populated_for_https(self) -> None:
        """SSL fields are populated for HTTPS URLs."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com",
            timeout=5,
        )

        mock_ssl_info = SSLCertInfo(
            issuer="Let's Encrypt",
            subject="example.com",
            expires_at=datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC),
            expires_in_days=365,
        )

        with patch("webstatuspi.monitor._get_ssl_cert_info") as mock_ssl:
            mock_ssl.return_value = (mock_ssl_info, None)

            with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.headers = {}
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)
                mock_urlopen.return_value = mock_response

                result = check_url(url_config)

        assert result.is_up is True
        assert result.ssl_cert_issuer == "Let's Encrypt"
        assert result.ssl_cert_subject == "example.com"
        assert result.ssl_cert_expires_in_days == 365
        assert result.ssl_cert_error is None

    def test_ssl_fields_none_for_http(self) -> None:
        """SSL fields are None for HTTP URLs."""
        url_config = UrlConfig(
            name="TEST",
            url="http://example.com",
            timeout=5,
        )

        with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check_url(url_config, allow_private=True)

        assert result.is_up is True
        assert result.ssl_cert_issuer is None
        assert result.ssl_cert_subject is None
        assert result.ssl_cert_expires_in_days is None
        assert result.ssl_cert_error is None

    def test_expired_ssl_cert_marks_down(self) -> None:
        """Expired SSL certificate marks URL as down."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com",
            timeout=5,
        )

        mock_ssl_info = SSLCertInfo(
            issuer="Let's Encrypt",
            subject="example.com",
            expires_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
            expires_in_days=-30,  # Expired 30 days ago
        )

        with patch("webstatuspi.monitor._get_ssl_cert_info") as mock_ssl:
            mock_ssl.return_value = (mock_ssl_info, None)

            with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.headers = {}
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)
                mock_urlopen.return_value = mock_response

                result = check_url(url_config)

        assert result.is_up is False
        assert "expired" in result.error_message.lower()
        assert result.ssl_cert_expires_in_days == -30

    def test_ssl_extraction_failure_does_not_affect_http_check(self) -> None:
        """SSL extraction failure doesn't mark URL as down if HTTP succeeds."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com",
            timeout=5,
        )

        with patch("webstatuspi.monitor._get_ssl_cert_info") as mock_ssl:
            mock_ssl.return_value = (None, "SSL extraction failed")

            with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.headers = {}
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)
                mock_urlopen.return_value = mock_response

                result = check_url(url_config)

        assert result.is_up is True  # HTTP check succeeded
        assert result.ssl_cert_error == "SSL extraction failed"
        assert result.ssl_cert_issuer is None

    def test_ssl_warning_threshold_logged(self) -> None:
        """SSL certificate approaching expiration is logged as warning."""
        url_config = UrlConfig(
            name="TEST",
            url="https://example.com",
            timeout=5,
        )

        mock_ssl_info = SSLCertInfo(
            issuer="Let's Encrypt",
            subject="example.com",
            expires_at=datetime(2025, 2, 1, 0, 0, 0, tzinfo=UTC),
            expires_in_days=15,  # Expires in 15 days (below 30 day threshold)
        )

        with patch("webstatuspi.monitor._get_ssl_cert_info") as mock_ssl:
            mock_ssl.return_value = (mock_ssl_info, None)

            with patch("webstatuspi.monitor._opener.open") as mock_urlopen:
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.headers = {}
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)
                mock_urlopen.return_value = mock_response

                with patch("webstatuspi.monitor.logger") as mock_logger:
                    result = check_url(url_config, ssl_warning_days=30)

                    # Verify warning was logged
                    mock_logger.warning.assert_called()
                    warning_call = mock_logger.warning.call_args[0]
                    assert "15 days" in str(warning_call) or "expires in" in str(warning_call).lower()

        assert result.is_up is True  # Still up, just a warning
        assert result.ssl_cert_expires_in_days == 15
