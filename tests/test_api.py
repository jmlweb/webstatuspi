"""Tests for the API module."""

import json
import socket
import sqlite3
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from webstatuspi.api import (
    ApiError,
    ApiServer,
    _build_status_response,
    _url_status_to_dict,
)
from webstatuspi.config import ApiConfig
from webstatuspi.database import _status_cache, init_db, insert_check
from webstatuspi.models import CheckResult, UrlStatus


@pytest.fixture
def db_conn(tmp_path: Path) -> sqlite3.Connection:
    """Create a database connection with initialized tables."""
    # Clear cache before test to avoid stale state from previous tests
    _status_cache._cached_result = None
    _status_cache._revalidating = False

    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    yield conn

    # Clear cache and wait briefly for any background threads to finish
    _status_cache._cached_result = None
    _status_cache._revalidating = False
    time.sleep(0.05)  # Allow background threads to complete or fail gracefully

    conn.close()


@pytest.fixture
def sample_status() -> UrlStatus:
    """Create a sample URL status."""
    return UrlStatus(
        url_name="TEST_URL",
        url="https://example.com",
        is_up=True,
        last_status_code=200,
        last_response_time_ms=150,
        last_error=None,
        last_check=datetime(2026, 1, 17, 10, 30, 0, tzinfo=UTC),
        checks_24h=24,
        uptime_24h=99.5,
    )


@pytest.fixture
def sample_check() -> CheckResult:
    """Create a sample check result."""
    return CheckResult(
        url_name="TEST_URL",
        url="https://example.com",
        status_code=200,
        response_time_ms=150,
        is_up=True,
        error_message=None,
        checked_at=datetime.now(UTC),
    )


def get_free_port() -> int:
    """Get a free port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class TestUrlStatusToDict:
    """Tests for _url_status_to_dict function."""

    def test_converts_all_fields(self, sample_status: UrlStatus) -> None:
        """All UrlStatus fields are converted to dict."""
        result = _url_status_to_dict(sample_status)

        assert result["name"] == "TEST_URL"
        assert result["url"] == "https://example.com"
        assert result["is_up"] is True
        assert result["status_code"] == 200
        assert result["response_time_ms"] == 150
        assert result["error"] is None
        assert result["last_check"] == "2026-01-17T10:30:00Z"
        assert result["checks_24h"] == 24
        assert result["uptime_24h"] == 99.5

    def test_handles_down_status(self) -> None:
        """Down status with error is converted correctly."""
        status = UrlStatus(
            url_name="DOWN_URL",
            url="https://down.example.com",
            is_up=False,
            last_status_code=None,
            last_response_time_ms=0,
            last_error="Connection refused",
            last_check=datetime(2026, 1, 17, 10, 30, 0, tzinfo=UTC),
            checks_24h=10,
            uptime_24h=50.0,
        )

        result = _url_status_to_dict(status)

        assert result["is_up"] is False
        assert result["status_code"] is None
        assert result["error"] == "Connection refused"

    def test_rounds_uptime(self) -> None:
        """Uptime percentage is rounded to 2 decimal places."""
        status = UrlStatus(
            url_name="ROUND_URL",
            url="https://round.example.com",
            is_up=True,
            last_status_code=200,
            last_response_time_ms=100,
            last_error=None,
            last_check=datetime(2026, 1, 17, 10, 30, 0, tzinfo=UTC),
            checks_24h=3,
            uptime_24h=66.66666666666667,
        )

        result = _url_status_to_dict(status)

        assert result["uptime_24h"] == 66.67


class TestBuildStatusResponse:
    """Tests for _build_status_response function."""

    def test_builds_response_with_summary(self, sample_status: UrlStatus) -> None:
        """Response includes urls array and summary."""
        result = _build_status_response([sample_status])

        assert "urls" in result
        assert "summary" in result
        assert len(result["urls"]) == 1
        assert result["summary"]["total"] == 1
        assert result["summary"]["up"] == 1
        assert result["summary"]["down"] == 0

    def test_counts_up_and_down(self) -> None:
        """Summary correctly counts up and down URLs."""
        statuses = [
            UrlStatus(
                url_name=f"URL_{i}",
                url=f"https://url{i}.example.com",
                is_up=i % 2 == 0,  # 0, 2, 4 are up
                last_status_code=200 if i % 2 == 0 else 500,
                last_response_time_ms=100,
                last_error=None if i % 2 == 0 else "Error",
                last_check=datetime(2026, 1, 17, 10, 30, 0, tzinfo=UTC),
                checks_24h=10,
                uptime_24h=100.0 if i % 2 == 0 else 0.0,
            )
            for i in range(5)
        ]

        result = _build_status_response(statuses)

        assert result["summary"]["total"] == 5
        assert result["summary"]["up"] == 3  # 0, 2, 4
        assert result["summary"]["down"] == 2  # 1, 3

    def test_handles_empty_list(self) -> None:
        """Empty status list returns zero counts."""
        result = _build_status_response([])

        assert result["urls"] == []
        assert result["summary"]["total"] == 0
        assert result["summary"]["up"] == 0
        assert result["summary"]["down"] == 0


class TestApiServer:
    """Tests for ApiServer class."""

    def test_starts_and_stops(self, db_conn: sqlite3.Connection) -> None:
        """Server starts and stops without errors."""
        port = get_free_port()
        config = ApiConfig(enabled=True, port=port)
        server = ApiServer(config, db_conn)

        server.start()
        assert server.is_running

        server.stop()
        assert not server.is_running

    def test_is_running_property(self, db_conn: sqlite3.Connection) -> None:
        """is_running reflects server state."""
        port = get_free_port()
        config = ApiConfig(enabled=True, port=port)
        server = ApiServer(config, db_conn)

        assert not server.is_running

        server.start()
        assert server.is_running

        server.stop()
        assert not server.is_running

    def test_start_twice_is_safe(self, db_conn: sqlite3.Connection) -> None:
        """Calling start() twice doesn't cause errors."""
        port = get_free_port()
        config = ApiConfig(enabled=True, port=port)
        server = ApiServer(config, db_conn)

        try:
            server.start()
            server.start()  # Should not raise
            assert server.is_running
        finally:
            server.stop()

    def test_stop_without_start_is_safe(self, db_conn: sqlite3.Connection) -> None:
        """Calling stop() without start() doesn't cause errors."""
        port = get_free_port()
        config = ApiConfig(enabled=True, port=port)
        server = ApiServer(config, db_conn)

        server.stop()  # Should not raise

    def test_raises_on_port_conflict(self, db_conn: sqlite3.Connection) -> None:
        """Raises ApiError when port is already in use."""
        port = get_free_port()
        config = ApiConfig(enabled=True, port=port)

        server1 = ApiServer(config, db_conn)
        server2 = ApiServer(config, db_conn)

        try:
            server1.start()
            with pytest.raises(ApiError):
                server2.start()
        finally:
            server1.stop()
            server2.stop()


class TestApiEndpoints:
    """Integration tests for API endpoints."""

    @pytest.fixture
    def running_server(self, db_conn: sqlite3.Connection) -> ApiServer:
        """Start a server and yield it, stopping after test."""
        port = get_free_port()
        config = ApiConfig(enabled=True, port=port)
        server = ApiServer(config, db_conn)
        server.start()
        # Give server time to start
        time.sleep(0.1)
        yield server
        server.stop()

    def _get(self, server: ApiServer, path: str) -> tuple:
        """Make a GET request and return (status_code, json_body)."""
        port = server.config.port
        url = f"http://localhost:{port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                body = json.loads(response.read().decode("utf-8"))
                return response.status, body
        except urllib.error.HTTPError as e:
            body = json.loads(e.read().decode("utf-8"))
            return e.code, body

    def test_health_endpoint(self, running_server: ApiServer) -> None:
        """GET /health returns ok status."""
        status, body = self._get(running_server, "/health")

        assert status == 200
        assert body == {"status": "ok"}

    def test_status_endpoint_empty(self, running_server: ApiServer) -> None:
        """GET /status returns empty list when no checks exist."""
        status, body = self._get(running_server, "/status")

        assert status == 200
        assert body["urls"] == []
        assert body["summary"]["total"] == 0

    def test_status_endpoint_with_data(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /status returns URL statuses."""
        check = CheckResult(
            url_name="API_TEST",
            url="https://api.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=datetime.now(UTC),
        )
        insert_check(db_conn, check)

        status, body = self._get(running_server, "/status")

        assert status == 200
        assert len(body["urls"]) == 1
        assert body["urls"][0]["name"] == "API_TEST"
        assert body["urls"][0]["is_up"] is True
        assert body["summary"]["total"] == 1
        assert body["summary"]["up"] == 1

    def test_status_by_name_found(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /status/<name> returns specific URL status."""
        check = CheckResult(
            url_name="SPECIFIC",
            url="https://specific.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=datetime.now(UTC),
        )
        insert_check(db_conn, check)

        status, body = self._get(running_server, "/status/SPECIFIC")

        assert status == 200
        assert body["name"] == "SPECIFIC"
        assert body["is_up"] is True

    def test_status_by_name_not_found(self, running_server: ApiServer) -> None:
        """GET /status/<name> returns 404 for unknown URL."""
        status, body = self._get(running_server, "/status/UNKNOWN")

        assert status == 404
        assert "error" in body
        assert "UNKNOWN" in body["error"]

    def test_not_found_endpoint(self, running_server: ApiServer) -> None:
        """Unknown paths return 404."""
        status, body = self._get(running_server, "/nonexistent")

        assert status == 404
        assert body == {"error": "Not found"}

    def test_json_content_type(self, running_server: ApiServer) -> None:
        """Responses have application/json content type."""
        port = running_server.config.port
        url = f"http://localhost:{port}/health"

        with urllib.request.urlopen(url, timeout=5) as response:
            content_type = response.headers.get("Content-Type")
            assert content_type == "application/json"

    def test_dashboard_endpoint(self, running_server: ApiServer) -> None:
        """GET / returns HTML dashboard."""
        port = running_server.config.port
        url = f"http://localhost:{port}/"

        with urllib.request.urlopen(url, timeout=5) as response:
            assert response.status == 200
            content_type = response.headers.get("Content-Type")
            assert "text/html" in content_type
            body = response.read().decode("utf-8")
            assert "<!DOCTYPE html>" in body
            assert "WebStatusπ" in body

    def test_dashboard_contains_required_elements(self, running_server: ApiServer) -> None:
        """Dashboard HTML contains all required UI elements."""
        port = running_server.config.port
        url = f"http://localhost:{port}/"

        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8")
            # Header elements
            assert "LIVE FEED" in body
            # Summary bar elements
            assert 'id="countUp"' in body
            assert 'id="countDown"' in body
            assert 'id="updatedTime"' in body
            # Cards container
            assert 'id="cardsContainer"' in body
            # JavaScript polling (uses fetchWithTimeout wrapper)
            assert "fetchWithTimeout('/status')" in body
            assert "setInterval" in body

    def test_dashboard_has_cache_header(self, running_server: ApiServer) -> None:
        """Dashboard response includes cache control header."""
        port = running_server.config.port
        url = f"http://localhost:{port}/"

        with urllib.request.urlopen(url, timeout=5) as response:
            cache_control = response.headers.get("Cache-Control")
            assert cache_control == "private, no-cache, must-revalidate"

    def test_dashboard_cyberpunk_styles(self, running_server: ApiServer) -> None:
        """Dashboard includes cyberpunk CSS styles."""
        port = running_server.config.port
        url = f"http://localhost:{port}/"

        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8")
            # Cyberpunk background colors
            assert "#0a0a0f" in body  # Main dark background
            assert "#12121a" in body  # Panel background
            # Neon status colors
            assert "#00ff66" in body  # UP green
            assert "#ff0040" in body  # DOWN red
            assert "#00fff9" in body  # Cyan accent
            # Mono font
            assert "JetBrains Mono" in body

    def test_dashboard_csp_nonce(self, running_server: ApiServer) -> None:
        """Dashboard uses nonce-based CSP instead of unsafe-inline."""
        import re

        port = running_server.config.port
        url = f"http://localhost:{port}/"

        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8")
            csp = response.headers.get("Content-Security-Policy", "")

            # Verify CSP contains nonce directive (not unsafe-inline)
            assert "'unsafe-inline'" not in csp
            assert "nonce-" in csp

            # Extract nonce from CSP header
            nonce_match = re.search(r"'nonce-([^']+)'", csp)
            assert nonce_match is not None, "CSP should contain a nonce"
            nonce = nonce_match.group(1)

            # Verify the same nonce is in the HTML style and script tags
            assert f'nonce="{nonce}"' in body, "Nonce should be in HTML tags"

            # Verify nonce is in both style and script tags
            style_nonce = re.search(r'<style[^>]*nonce="([^"]+)"', body)
            script_nonce = re.search(r'<script[^>]*nonce="([^"]+)"', body)
            assert style_nonce is not None, "Style tag should have nonce"
            assert script_nonce is not None, "Script tag should have nonce"
            assert style_nonce.group(1) == nonce, "Style nonce should match CSP nonce"
            assert script_nonce.group(1) == nonce, "Script nonce should match CSP nonce"


class TestHistoryEndpoint:
    """Tests for GET /history/<name> endpoint."""

    @pytest.fixture
    def running_server(self, db_conn: sqlite3.Connection) -> ApiServer:
        """Start a server and yield it, stopping after test."""
        port = get_free_port()
        config = ApiConfig(enabled=True, port=port)
        server = ApiServer(config, db_conn)
        server.start()
        time.sleep(0.1)
        yield server
        server.stop()

    def _get(self, server: ApiServer, path: str) -> tuple:
        """Make a GET request and return (status_code, json_body)."""
        port = server.config.port
        url = f"http://localhost:{port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                body = json.loads(response.read().decode("utf-8"))
                return response.status, body
        except urllib.error.HTTPError as e:
            body = json.loads(e.read().decode("utf-8"))
            return e.code, body

    def test_history_returns_checks(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /history/<name> returns check history ordered by time."""
        # Insert multiple checks
        for i in range(3):
            check = CheckResult(
                url_name="HIST_TEST",
                url="https://history.example.com",
                status_code=200 if i % 2 == 0 else 500,
                response_time_ms=100 + i * 10,
                is_up=i % 2 == 0,
                error_message=None if i % 2 == 0 else "Server error",
                checked_at=datetime.now(UTC),
            )
            insert_check(db_conn, check)
            time.sleep(0.01)  # Ensure different timestamps

        status, body = self._get(running_server, "/history/HIST_TEST")

        assert status == 200
        assert body["name"] == "HIST_TEST"
        assert body["count"] == 3
        assert len(body["checks"]) == 3
        # Should be ordered newest first
        assert body["checks"][0]["response_time_ms"] == 120

    def test_history_not_found(self, running_server: ApiServer) -> None:
        """GET /history/<name> returns 404 for unknown URL."""
        status, body = self._get(running_server, "/history/UNKNOWN")

        assert status == 404
        assert "error" in body
        assert "UNKNOWN" in body["error"]

    def test_history_empty(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /history/<name> returns empty list if no recent checks."""
        # Insert a check with old timestamp (outside 24h window)
        old_time = datetime.now(UTC) - timedelta(hours=25)
        check = CheckResult(
            url_name="OLD_URL",
            url="https://old.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=old_time,
        )
        insert_check(db_conn, check)

        status, body = self._get(running_server, "/history/OLD_URL")

        assert status == 200
        assert body["name"] == "OLD_URL"
        assert body["count"] == 0
        assert body["checks"] == []

    def test_history_check_fields(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /history/<name> returns correct fields in each check."""
        check = CheckResult(
            url_name="FIELDS",
            url="https://fields.example.com",
            status_code=503,
            response_time_ms=250,
            is_up=False,
            error_message="Service unavailable",
            checked_at=datetime.now(UTC),
        )
        insert_check(db_conn, check)

        status, body = self._get(running_server, "/history/FIELDS")

        assert status == 200
        assert len(body["checks"]) == 1

        check_data = body["checks"][0]
        assert "checked_at" in check_data
        assert check_data["checked_at"].endswith("Z")
        assert check_data["is_up"] is False
        assert check_data["status_code"] == 503
        assert check_data["response_time_ms"] == 250
        assert check_data["error"] == "Service unavailable"

    def test_history_limits_to_100(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /history/<name> limits results to 100 checks."""
        # Insert 110 checks
        for i in range(110):
            check = CheckResult(
                url_name="LIMIT_TEST",
                url="https://limit.example.com",
                status_code=200,
                response_time_ms=100,
                is_up=True,
                error_message=None,
                checked_at=datetime.now(UTC),
            )
            insert_check(db_conn, check)

        status, body = self._get(running_server, "/history/LIMIT_TEST")

        assert status == 200
        assert body["count"] == 100
        assert len(body["checks"]) == 100


class TestResetEndpoint:
    """Tests for DELETE /reset endpoint."""

    @pytest.fixture
    def running_server(self, db_conn: sqlite3.Connection) -> ApiServer:
        """Create a running API server with database."""
        port = get_free_port()
        config = ApiConfig(enabled=True, port=port)
        server = ApiServer(config, db_conn)
        server.start()
        # Give server time to start
        time.sleep(0.1)
        yield server
        server.stop()

    def _delete(self, server: ApiServer, path: str, headers: dict = None) -> tuple:
        """Make a DELETE request and return (status_code, json_body)."""
        port = server.config.port
        url = f"http://localhost:{port}{path}"
        try:
            request = urllib.request.Request(url, method="DELETE")
            if headers:
                for key, value in headers.items():
                    request.add_header(key, value)
            with urllib.request.urlopen(request, timeout=5) as response:
                body = json.loads(response.read().decode("utf-8"))
                return response.status, body
        except urllib.error.HTTPError as e:
            body = json.loads(e.read().decode("utf-8"))
            return e.code, body

    def test_reset_deletes_all_checks(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """DELETE /reset deletes all check records."""
        # Insert some checks
        for i in range(5):
            check = CheckResult(
                url_name="RESET_TEST",
                url="https://reset.example.com",
                status_code=200,
                response_time_ms=100,
                is_up=True,
                error_message=None,
                checked_at=datetime.now(UTC),
            )
            insert_check(db_conn, check)

        # Verify checks exist
        cursor = db_conn.execute("SELECT COUNT(*) FROM checks")
        count_before = cursor.fetchone()[0]
        assert count_before == 5

        # Call reset endpoint
        status, body = self._delete(running_server, "/reset")

        # Verify success response
        assert status == 200
        assert body["success"] is True
        assert body["deleted"] == 5

        # Verify checks are deleted
        cursor = db_conn.execute("SELECT COUNT(*) FROM checks")
        count_after = cursor.fetchone()[0]
        assert count_after == 0

    def test_reset_with_no_checks(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """DELETE /reset returns 0 deleted when database is empty."""
        status, body = self._delete(running_server, "/reset")

        assert status == 200
        assert body["success"] is True
        assert body["deleted"] == 0

    def test_reset_returns_deleted_count(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """DELETE /reset returns correct count of deleted records."""
        # Insert checks
        for i in range(3):
            check = CheckResult(
                url_name="COUNT_TEST",
                url="https://count.example.com",
                status_code=200,
                response_time_ms=100,
                is_up=True,
                error_message=None,
                checked_at=datetime.now(UTC),
            )
            insert_check(db_conn, check)

        status, body = self._delete(running_server, "/reset")

        assert status == 200
        assert body["deleted"] == 3

    def test_reset_nonexistent_endpoint_404(self, running_server: ApiServer) -> None:
        """DELETE to nonexistent endpoint returns 404."""
        status, body = self._delete(running_server, "/nonexistent")

        assert status == 404
        assert "error" in body

    def test_reset_blocked_from_cloudflare(self, running_server: ApiServer) -> None:
        """DELETE /reset is blocked when request comes through Cloudflare."""
        # Test with CF-Connecting-IP header
        status, body = self._delete(running_server, "/reset", headers={"CF-Connecting-IP": "1.2.3.4"})
        assert status == 403
        assert "Nice try, Diddy!" in body["error"]

        # Test with CF-Ray header
        status, body = self._delete(running_server, "/reset", headers={"CF-Ray": "abc123"})
        assert status == 403
        assert "not allowed" in body["error"]

        # Test with CF-IPCountry header
        status, body = self._delete(running_server, "/reset", headers={"CF-IPCountry": "US"})
        assert status == 403
        assert "not allowed" in body["error"]


class TestPrometheusMetrics:
    """Tests for GET /metrics endpoint (Prometheus format)."""

    @pytest.fixture
    def running_server(self, db_conn: sqlite3.Connection) -> ApiServer:
        """Start a server and yield it, stopping after test."""
        port = get_free_port()
        config = ApiConfig(enabled=True, port=port)
        server = ApiServer(config, db_conn)
        server.start()
        time.sleep(0.1)
        yield server
        server.stop()

    def _get_text(self, server: ApiServer, path: str) -> tuple:
        """Make a GET request and return (status_code, text_body)."""
        port = server.config.port
        url = f"http://localhost:{port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                body = response.read().decode("utf-8")
                return response.status, body
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            return e.code, body

    def test_metrics_endpoint_returns_text(self, running_server: ApiServer) -> None:
        """GET /metrics returns plain text with Prometheus format."""
        port = running_server.config.port
        url = f"http://localhost:{port}/metrics"

        with urllib.request.urlopen(url, timeout=5) as response:
            assert response.status == 200
            content_type = response.headers.get("Content-Type")
            assert "text/plain" in content_type
            assert "version=0.0.4" in content_type

    def test_metrics_empty_database(self, running_server: ApiServer) -> None:
        """GET /metrics returns valid format with empty database."""
        status, body = self._get_text(running_server, "/metrics")

        assert status == 200
        # Should have HELP and TYPE headers even with no data
        assert "# HELP webstatuspi_uptime_percentage" in body
        assert "# TYPE webstatuspi_uptime_percentage gauge" in body
        assert "# HELP webstatuspi_response_time_ms" in body
        assert "# TYPE webstatuspi_response_time_ms gauge" in body
        assert "# HELP webstatuspi_checks_total" in body
        assert "# TYPE webstatuspi_checks_total counter" in body
        assert "# HELP webstatuspi_last_check_timestamp" in body
        assert "# TYPE webstatuspi_last_check_timestamp gauge" in body

    def test_metrics_with_data(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /metrics returns metrics for monitored URLs."""
        # Insert test checks
        check = CheckResult(
            url_name="PROM_TEST",
            url="https://prometheus.example.com",
            status_code=200,
            response_time_ms=150,
            is_up=True,
            error_message=None,
            checked_at=datetime.now(UTC),
        )
        insert_check(db_conn, check)

        status, body = self._get_text(running_server, "/metrics")

        assert status == 200
        # Check uptime metric
        assert 'webstatuspi_uptime_percentage{url_name="PROM_TEST",url="https://prometheus.example.com"}' in body
        # Check response time metrics
        assert (
            'webstatuspi_response_time_ms{url_name="PROM_TEST",url="https://prometheus.example.com",type="avg"}' in body
        )
        assert (
            'webstatuspi_response_time_ms{url_name="PROM_TEST",url="https://prometheus.example.com",type="min"}' in body
        )
        assert (
            'webstatuspi_response_time_ms{url_name="PROM_TEST",url="https://prometheus.example.com",type="max"}' in body
        )
        # Check checks total
        assert (
            'webstatuspi_checks_total{url_name="PROM_TEST",url="https://prometheus.example.com",status="success"}'
            in body
        )
        assert (
            'webstatuspi_checks_total{url_name="PROM_TEST",url="https://prometheus.example.com",status="failure"}'
            in body
        )
        # Check timestamp
        assert 'webstatuspi_last_check_timestamp{url_name="PROM_TEST",url="https://prometheus.example.com"}' in body

    def test_metrics_label_escaping(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /metrics properly escapes special characters in labels."""
        # URL with special characters
        check = CheckResult(
            url_name='TEST"URL',
            url='https://example.com/path?query="value"',
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=datetime.now(UTC),
        )
        insert_check(db_conn, check)

        status, body = self._get_text(running_server, "/metrics")

        assert status == 200
        # Labels should have escaped quotes
        assert 'url_name="TEST\\"URL"' in body
        assert 'url="https://example.com/path?query=\\"value\\""' in body

    def test_metrics_multiple_urls(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /metrics includes metrics for all monitored URLs."""
        # Insert checks for multiple URLs
        for i in range(3):
            check = CheckResult(
                url_name=f"URL_{i}",
                url=f"https://url{i}.example.com",
                status_code=200,
                response_time_ms=100 + i * 10,
                is_up=True,
                error_message=None,
                checked_at=datetime.now(UTC),
            )
            insert_check(db_conn, check)

        status, body = self._get_text(running_server, "/metrics")

        assert status == 200
        # All URLs should be present
        for i in range(3):
            assert f'url_name="URL_{i}"' in body
            assert f'url="https://url{i}.example.com"' in body

    def test_metrics_success_failure_counts(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /metrics calculates success and failure counts correctly."""
        # Insert 10 checks: 8 success, 2 failures
        for i in range(10):
            check = CheckResult(
                url_name="COUNT_TEST",
                url="https://count.example.com",
                status_code=200 if i < 8 else 500,
                response_time_ms=100,
                is_up=i < 8,
                error_message=None if i < 8 else "Error",
                checked_at=datetime.now(UTC),
            )
            insert_check(db_conn, check)
            time.sleep(0.001)  # Ensure different timestamps

        status, body = self._get_text(running_server, "/metrics")

        assert status == 200
        # Parse success and failure counts
        lines = body.split("\n")
        success_line = [
            line
            for line in lines
            if 'url_name="COUNT_TEST"' in line and 'status="success"' in line and "webstatuspi_checks_total" in line
        ]
        failure_line = [
            line
            for line in lines
            if 'url_name="COUNT_TEST"' in line and 'status="failure"' in line and "webstatuspi_checks_total" in line
        ]

        assert len(success_line) == 1
        assert len(failure_line) == 1
        # Success count should be 8, failure count should be 2
        assert success_line[0].endswith(" 8")
        assert failure_line[0].endswith(" 2")

    def test_metrics_timestamp_format(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /metrics includes Unix timestamp for last check."""
        now = datetime.now(UTC)
        check = CheckResult(
            url_name="TIME_TEST",
            url="https://time.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=now,
        )
        insert_check(db_conn, check)

        status, body = self._get_text(running_server, "/metrics")

        assert status == 200
        # Find timestamp line
        lines = body.split("\n")
        timestamp_line = [
            line for line in lines if 'url_name="TIME_TEST"' in line and "webstatuspi_last_check_timestamp" in line
        ]

        assert len(timestamp_line) == 1
        # Extract timestamp value
        timestamp_str = timestamp_line[0].split()[-1]
        timestamp = int(timestamp_str)

        # Timestamp should be close to now (within 5 seconds)
        expected_timestamp = int(now.timestamp())
        assert abs(timestamp - expected_timestamp) <= 5

    def test_metrics_response_time_types(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /metrics includes avg, min, max response time metrics."""
        # Insert checks with different response times
        for rt in [100, 150, 200, 250, 300]:
            check = CheckResult(
                url_name="RT_TEST",
                url="https://rt.example.com",
                status_code=200,
                response_time_ms=rt,
                is_up=True,
                error_message=None,
                checked_at=datetime.now(UTC),
            )
            insert_check(db_conn, check)
            time.sleep(0.001)

        status, body = self._get_text(running_server, "/metrics")

        assert status == 200
        lines = body.split("\n")

        # Find response time metrics
        avg_line = [line for line in lines if 'url_name="RT_TEST"' in line and 'type="avg"' in line]
        min_line = [line for line in lines if 'url_name="RT_TEST"' in line and 'type="min"' in line]
        max_line = [line for line in lines if 'url_name="RT_TEST"' in line and 'type="max"' in line]

        assert len(avg_line) == 1
        assert len(min_line) == 1
        assert len(max_line) == 1

        # Extract values
        avg_value = float(avg_line[0].split()[-1])
        min_value = float(min_line[0].split()[-1])
        max_value = float(max_line[0].split()[-1])

        # Validate values
        assert min_value == 100.0
        assert max_value == 300.0
        assert 190.0 <= avg_value <= 210.0  # Average should be 200


class TestPwaEndpoints:
    """Tests for Progressive Web App (PWA) endpoints."""

    @pytest.fixture
    def running_server(self, db_conn: sqlite3.Connection) -> ApiServer:
        """Start a server and yield it, stopping after test."""
        port = get_free_port()
        config = ApiConfig(enabled=True, port=port)
        server = ApiServer(config, db_conn)
        server.start()
        time.sleep(0.1)
        yield server
        server.stop()

    def test_manifest_endpoint(self, running_server: ApiServer) -> None:
        """GET /manifest.json returns valid manifest."""
        port = running_server.config.port
        url = f"http://localhost:{port}/manifest.json"

        with urllib.request.urlopen(url, timeout=5) as response:
            assert response.status == 200
            content_type = response.headers.get("Content-Type")
            assert "application/manifest+json" in content_type

            body = json.loads(response.read().decode("utf-8"))
            # Required manifest fields
            assert body["name"] == "WebStatusπ // SYSTEM MONITOR"
            assert body["short_name"] == "WebStatusπ"
            assert body["start_url"] == "/"
            assert body["display"] == "standalone"
            assert body["background_color"] == "#0a0a0f"
            assert body["theme_color"] == "#00fff9"
            # Icons
            assert len(body["icons"]) >= 2
            icon_sizes = [icon["sizes"] for icon in body["icons"]]
            assert "192x192" in icon_sizes
            assert "512x512" in icon_sizes

    def test_manifest_caching(self, running_server: ApiServer) -> None:
        """Manifest has appropriate cache headers."""
        port = running_server.config.port
        url = f"http://localhost:{port}/manifest.json"

        with urllib.request.urlopen(url, timeout=5) as response:
            cache_control = response.headers.get("Cache-Control")
            assert "max-age=3600" in cache_control

    def test_service_worker_endpoint(self, running_server: ApiServer) -> None:
        """GET /sw.js returns valid service worker."""
        port = running_server.config.port
        url = f"http://localhost:{port}/sw.js"

        with urllib.request.urlopen(url, timeout=5) as response:
            assert response.status == 200
            content_type = response.headers.get("Content-Type")
            assert "application/javascript" in content_type

            body = response.read().decode("utf-8")
            # Service worker content
            assert "SW_VERSION" in body
            assert "addEventListener" in body
            assert "install" in body
            assert "activate" in body
            assert "fetch" in body

    def test_service_worker_no_cache(self, running_server: ApiServer) -> None:
        """Service worker has no-cache headers for update detection."""
        port = running_server.config.port
        url = f"http://localhost:{port}/sw.js"

        with urllib.request.urlopen(url, timeout=5) as response:
            cache_control = response.headers.get("Cache-Control")
            assert "no-cache" in cache_control
            assert "no-store" in cache_control

    def test_icon_192_endpoint(self, running_server: ApiServer) -> None:
        """GET /icon-192.png returns PNG image."""
        port = running_server.config.port
        url = f"http://localhost:{port}/icon-192.png"

        with urllib.request.urlopen(url, timeout=5) as response:
            assert response.status == 200
            content_type = response.headers.get("Content-Type")
            assert "image/png" in content_type

            body = response.read()
            # PNG magic bytes
            assert body[:8] == b"\x89PNG\r\n\x1a\n"

    def test_icon_512_endpoint(self, running_server: ApiServer) -> None:
        """GET /icon-512.png returns PNG image."""
        port = running_server.config.port
        url = f"http://localhost:{port}/icon-512.png"

        with urllib.request.urlopen(url, timeout=5) as response:
            assert response.status == 200
            content_type = response.headers.get("Content-Type")
            assert "image/png" in content_type

            body = response.read()
            # PNG magic bytes
            assert body[:8] == b"\x89PNG\r\n\x1a\n"

    def test_icon_caching(self, running_server: ApiServer) -> None:
        """Icons have long cache headers."""
        port = running_server.config.port
        url = f"http://localhost:{port}/icon-192.png"

        with urllib.request.urlopen(url, timeout=5) as response:
            cache_control = response.headers.get("Cache-Control")
            assert "max-age=604800" in cache_control
            assert "immutable" in cache_control

    def test_dashboard_has_pwa_meta_tags(self, running_server: ApiServer) -> None:
        """Dashboard includes PWA meta tags and manifest link."""
        port = running_server.config.port
        url = f"http://localhost:{port}/"

        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8")

            # PWA meta tags
            assert 'name="theme-color"' in body
            assert 'content="#00fff9"' in body
            assert 'name="apple-mobile-web-app-capable"' in body
            assert 'name="apple-mobile-web-app-title"' in body

            # Manifest link
            assert 'rel="manifest"' in body
            assert 'href="/manifest.json"' in body

            # Apple touch icon
            assert 'rel="apple-touch-icon"' in body

    def test_dashboard_has_service_worker_registration(self, running_server: ApiServer) -> None:
        """Dashboard includes service worker registration code."""
        port = running_server.config.port
        url = f"http://localhost:{port}/"

        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8")

            # Service worker registration
            assert "serviceWorker" in body
            assert "register('/sw.js')" in body

    def test_dashboard_has_offline_detection(self, running_server: ApiServer) -> None:
        """Dashboard includes offline detection code."""
        port = running_server.config.port
        url = f"http://localhost:{port}/"

        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8")

            # Offline banner
            assert 'id="offlineBanner"' in body
            assert "OFFLINE MODE" in body

            # Online/offline event listeners
            assert "addEventListener('online'" in body or 'addEventListener("online"' in body
            assert "addEventListener('offline'" in body or 'addEventListener("offline"' in body


class TestBadgeEndpoint:
    """Tests for GET /badge.svg endpoint."""

    @pytest.fixture
    def running_server(self, db_conn: sqlite3.Connection) -> ApiServer:
        """Start a server and yield it, stopping after test."""
        port = get_free_port()
        config = ApiConfig(enabled=True, port=port)
        server = ApiServer(config, db_conn)
        server.start()
        time.sleep(0.1)
        yield server
        server.stop()

    def _get_svg(self, server: ApiServer, path: str) -> tuple:
        """Make a GET request and return (status_code, svg_body)."""
        port = server.config.port
        url = f"http://localhost:{port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                body = response.read().decode("utf-8")
                content_type = response.headers.get("Content-Type", "")
                return response.status, body, content_type
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            return e.code, body, ""

    def test_badge_returns_svg(self, running_server: ApiServer) -> None:
        """GET /badge.svg returns SVG content type."""
        status, body, content_type = self._get_svg(running_server, "/badge.svg")
        assert status == 200
        assert "image/svg+xml" in content_type
        assert "<svg" in body
        assert "</svg>" in body

    def test_badge_unknown_status_empty_db(self, running_server: ApiServer) -> None:
        """GET /badge.svg returns unknown status when database is empty."""
        status, body, _ = self._get_svg(running_server, "/badge.svg")
        assert status == 200
        assert "UNKNOWN" in body
        assert "#9f9f9f" in body  # gray color

    def test_badge_up_status_all_services_up(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /badge.svg returns UP when all services are up."""
        check = CheckResult(
            url_name="BADGE_TEST",
            url="https://badge.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=datetime.now(UTC),
        )
        insert_check(db_conn, check)

        status, body, _ = self._get_svg(running_server, "/badge.svg")
        assert status == 200
        assert "UP" in body
        assert "#4c1" in body  # green color

    def test_badge_down_status_all_services_down(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /badge.svg returns DOWN when all services are down."""
        check = CheckResult(
            url_name="BADGE_DOWN",
            url="https://down.example.com",
            status_code=500,
            response_time_ms=0,
            is_up=False,
            error_message="Server error",
            checked_at=datetime.now(UTC),
        )
        insert_check(db_conn, check)

        status, body, _ = self._get_svg(running_server, "/badge.svg")
        assert status == 200
        assert "DOWN" in body
        assert "#e05d44" in body  # red color

    def test_badge_degraded_status_mixed(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /badge.svg returns DEGRADED when some services are down."""
        # Insert one up, one down
        check_up = CheckResult(
            url_name="UP_SVC",
            url="https://up.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=datetime.now(UTC),
        )
        check_down = CheckResult(
            url_name="DOWN_SVC",
            url="https://down.example.com",
            status_code=500,
            response_time_ms=0,
            is_up=False,
            error_message="Error",
            checked_at=datetime.now(UTC),
        )
        insert_check(db_conn, check_up)
        insert_check(db_conn, check_down)

        status, body, _ = self._get_svg(running_server, "/badge.svg")
        assert status == 200
        assert "DEGRADED" in body
        assert "#dfb317" in body  # yellow color

    def test_badge_specific_service_up(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /badge.svg?url=SERVICE returns status for specific service."""
        check = CheckResult(
            url_name="MY_SVC",
            url="https://mysvc.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=datetime.now(UTC),
        )
        insert_check(db_conn, check)

        status, body, _ = self._get_svg(running_server, "/badge.svg?url=MY_SVC")
        assert status == 200
        assert "MY_SVC" in body  # label should be service name
        assert "UP" in body
        assert "#4c1" in body  # green

    def test_badge_specific_service_down(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /badge.svg?url=SERVICE returns DOWN for down service."""
        check = CheckResult(
            url_name="FAIL_SVC",
            url="https://fail.example.com",
            status_code=503,
            response_time_ms=0,
            is_up=False,
            error_message="Service unavailable",
            checked_at=datetime.now(UTC),
        )
        insert_check(db_conn, check)

        status, body, _ = self._get_svg(running_server, "/badge.svg?url=FAIL_SVC")
        assert status == 200
        assert "FAIL_SVC" in body
        assert "DOWN" in body
        assert "#e05d44" in body  # red

    def test_badge_specific_service_not_found(self, running_server: ApiServer) -> None:
        """GET /badge.svg?url=UNKNOWN returns 404."""
        status, body, _ = self._get_svg(running_server, "/badge.svg?url=UNKNOWN")
        assert status == 404
        assert "not found" in body.lower()

    def test_badge_flat_style(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /badge.svg?style=flat returns flat badge without gradient."""
        check = CheckResult(
            url_name="FLAT_TEST",
            url="https://flat.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=datetime.now(UTC),
        )
        insert_check(db_conn, check)

        status, body, _ = self._get_svg(running_server, "/badge.svg?style=flat")
        assert status == 200
        assert "<svg" in body
        # Flat style should NOT have gradient elements
        assert "linearGradient" not in body
        assert "mask" not in body

    def test_badge_default_style_has_gradient(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /badge.svg returns default style with gradient."""
        check = CheckResult(
            url_name="GRAD_TEST",
            url="https://grad.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=datetime.now(UTC),
        )
        insert_check(db_conn, check)

        status, body, _ = self._get_svg(running_server, "/badge.svg")
        assert status == 200
        # Default style should have gradient elements
        assert "linearGradient" in body
        assert "mask" in body

    def test_badge_combined_params(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /badge.svg?url=SERVICE&style=flat works with both params."""
        check = CheckResult(
            url_name="COMBO",
            url="https://combo.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=datetime.now(UTC),
        )
        insert_check(db_conn, check)

        status, body, _ = self._get_svg(running_server, "/badge.svg?url=COMBO&style=flat")
        assert status == 200
        assert "COMBO" in body
        assert "UP" in body
        assert "linearGradient" not in body  # flat style

    def test_badge_invalid_style_uses_default(self, running_server: ApiServer, db_conn: sqlite3.Connection) -> None:
        """GET /badge.svg?style=invalid falls back to default style."""
        check = CheckResult(
            url_name="STYLE_FB",
            url="https://style.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=datetime.now(UTC),
        )
        insert_check(db_conn, check)

        status, body, _ = self._get_svg(running_server, "/badge.svg?style=invalid")
        assert status == 200
        # Should use default style (with gradient)
        assert "linearGradient" in body

    def test_badge_has_cache_header(self, running_server: ApiServer) -> None:
        """Badge response includes cache control header."""
        port = running_server.config.port
        url = f"http://localhost:{port}/badge.svg"
        with urllib.request.urlopen(url, timeout=5) as response:
            cache_control = response.headers.get("Cache-Control")
            assert "max-age=60" in cache_control  # 1 minute cache
