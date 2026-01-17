"""Tests for the API module."""

import json
import socket
import sqlite3
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

import pytest

from webstatuspi.api import (
    ApiError,
    ApiServer,
    StatusHandler,
    _build_status_response,
    _create_handler_class,
    _url_status_to_dict,
)
from webstatuspi.config import ApiConfig
from webstatuspi.database import init_db, insert_check
from webstatuspi.models import CheckResult, UrlStatus


@pytest.fixture
def db_conn(tmp_path: Path) -> sqlite3.Connection:
    """Create a database connection with initialized tables."""
    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    yield conn
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
        last_check=datetime(2026, 1, 17, 10, 30, 0),
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
        checked_at=datetime.utcnow(),
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
            last_check=datetime(2026, 1, 17, 10, 30, 0),
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
            last_check=datetime(2026, 1, 17, 10, 30, 0),
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
                last_check=datetime(2026, 1, 17, 10, 30, 0),
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
    def running_server(
        self, db_conn: sqlite3.Connection
    ) -> ApiServer:
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

    def test_status_endpoint_with_data(
        self, running_server: ApiServer, db_conn: sqlite3.Connection
    ) -> None:
        """GET /status returns URL statuses."""
        check = CheckResult(
            url_name="API_TEST",
            url="https://api.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=datetime.utcnow(),
        )
        insert_check(db_conn, check)

        status, body = self._get(running_server, "/status")

        assert status == 200
        assert len(body["urls"]) == 1
        assert body["urls"][0]["name"] == "API_TEST"
        assert body["urls"][0]["is_up"] is True
        assert body["summary"]["total"] == 1
        assert body["summary"]["up"] == 1

    def test_status_by_name_found(
        self, running_server: ApiServer, db_conn: sqlite3.Connection
    ) -> None:
        """GET /status/<name> returns specific URL status."""
        check = CheckResult(
            url_name="SPECIFIC",
            url="https://specific.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=datetime.utcnow(),
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

    def test_json_content_type(
        self, running_server: ApiServer
    ) -> None:
        """Responses have application/json content type."""
        port = running_server.config.port
        url = f"http://localhost:{port}/health"

        with urllib.request.urlopen(url, timeout=5) as response:
            content_type = response.headers.get("Content-Type")
            assert content_type == "application/json"
