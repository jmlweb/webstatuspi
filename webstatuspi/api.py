"""HTTP API server for URL monitoring status."""

import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional

from .config import ApiConfig
from .database import get_history, get_latest_status, DatabaseError
from .models import UrlStatus
from ._dashboard import HTML_DASHBOARD

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Raised when an API operation fails."""
    pass


def _url_status_to_dict(status: UrlStatus) -> Dict[str, Any]:
    """Convert a UrlStatus object to a JSON-serializable dictionary."""
    return {
        "name": status.url_name,
        "url": status.url,
        "is_up": status.is_up,
        "status_code": status.last_status_code,
        "response_time_ms": status.last_response_time_ms,
        "error": status.last_error,
        "last_check": status.last_check.isoformat() + "Z",
        "checks_24h": status.checks_24h,
        "uptime_24h": round(status.uptime_24h, 2),
    }


def _build_status_response(statuses: List[UrlStatus]) -> Dict[str, Any]:
    """Build the full status response with summary."""
    urls_data = [_url_status_to_dict(s) for s in statuses]
    up_count = sum(1 for s in statuses if s.is_up)

    return {
        "urls": urls_data,
        "summary": {
            "total": len(statuses),
            "up": up_count,
            "down": len(statuses) - up_count,
        },
    }


class StatusHandler(BaseHTTPRequestHandler):
    """HTTP request handler for status API endpoints."""

    # Class-level reference to database connection (set by factory)
    db_conn: Optional[sqlite3.Connection] = None

    def log_message(self, format: str, *args: Any) -> None:
        """Override to use Python logging instead of stderr."""
        logger.debug("API %s - %s", self.address_string(), format % args)

    def _send_json(self, code: int, data: Dict[str, Any]) -> None:
        """Send a JSON response with the given status code."""
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, code: int, message: str) -> None:
        """Send a JSON error response."""
        self._send_json(code, {"error": message})

    def _send_html(self, code: int, html: str) -> None:
        """Send an HTML response with the given status code."""
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "max-age=3600")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        """Handle GET requests."""
        try:
            if self.path == "/":
                self._handle_dashboard()
            elif self.path == "/health":
                self._handle_health()
            elif self.path == "/status":
                self._handle_status_all()
            elif self.path.startswith("/status/"):
                name = self.path[8:]  # Extract name after /status/
                if name:
                    self._handle_status_by_name(name)
                else:
                    self._send_error_json(400, "URL name is required")
            elif self.path.startswith("/history/"):
                name = self.path[9:]  # Extract name after /history/
                if name:
                    self._handle_history_by_name(name)
                else:
                    self._send_error_json(400, "URL name is required")
            else:
                self._send_error_json(404, "Not found")
        except Exception as e:
            logger.exception("Error handling request: %s", e)
            self._send_error_json(500, "Internal server error")

    def _handle_dashboard(self) -> None:
        """Handle GET / endpoint - serve HTML dashboard."""
        self._send_html(200, HTML_DASHBOARD)

    def _handle_health(self) -> None:
        """Handle GET /health endpoint."""
        self._send_json(200, {"status": "ok"})

    def _handle_status_all(self) -> None:
        """Handle GET /status endpoint."""
        if self.db_conn is None:
            self._send_error_json(503, "Database not available")
            return

        try:
            statuses = get_latest_status(self.db_conn)
            response = _build_status_response(statuses)
            self._send_json(200, response)
        except DatabaseError as e:
            logger.error("Database error in /status: %s", e)
            self._send_error_json(500, "Database error")

    def _handle_status_by_name(self, name: str) -> None:
        """Handle GET /status/<name> endpoint."""
        if self.db_conn is None:
            self._send_error_json(503, "Database not available")
            return

        try:
            statuses = get_latest_status(self.db_conn)
            matching = [s for s in statuses if s.url_name == name]

            if not matching:
                self._send_error_json(404, f"URL '{name}' not found")
                return

            response = _url_status_to_dict(matching[0])
            self._send_json(200, response)
        except DatabaseError as e:
            logger.error("Database error in /status/%s: %s", name, e)
            self._send_error_json(500, "Database error")

    def _handle_history_by_name(self, name: str) -> None:
        """Handle GET /history/<name> endpoint."""
        if self.db_conn is None:
            self._send_error_json(503, "Database not available")
            return

        try:
            # First check if the URL exists
            statuses = get_latest_status(self.db_conn)
            matching = [s for s in statuses if s.url_name == name]

            if not matching:
                self._send_error_json(404, f"URL '{name}' not found")
                return

            # Get history for the last 24 hours, limited to 100 checks
            since = datetime.utcnow() - timedelta(hours=24)
            checks = get_history(self.db_conn, name, since, limit=100)

            response = {
                "name": name,
                "checks": [
                    {
                        "checked_at": c.checked_at.isoformat() + "Z",
                        "is_up": c.is_up,
                        "status_code": c.status_code,
                        "response_time_ms": c.response_time_ms,
                        "error": c.error_message,
                    }
                    for c in checks
                ],
                "count": len(checks),
            }
            self._send_json(200, response)
        except DatabaseError as e:
            logger.error("Database error in /history/%s: %s", name, e)
            self._send_error_json(500, "Database error")


def _create_handler_class(db_conn: sqlite3.Connection) -> type:
    """Create a handler class with the database connection bound."""

    class BoundStatusHandler(StatusHandler):
        pass

    BoundStatusHandler.db_conn = db_conn
    return BoundStatusHandler


class ApiServer:
    """Threaded HTTP API server for URL monitoring status."""

    def __init__(
        self,
        config: ApiConfig,
        db_conn: sqlite3.Connection,
    ) -> None:
        """Initialize the API server.

        Args:
            config: API configuration.
            db_conn: Database connection for querying status.
        """
        self.config = config
        self.db_conn = db_conn
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

    def start(self) -> None:
        """Start the API server in a background thread.

        Raises:
            ApiError: If the server fails to start.
        """
        if self._thread is not None and self._thread.is_alive():
            logger.warning("API server is already running")
            return

        try:
            handler_class = _create_handler_class(self.db_conn)
            self._server = HTTPServer(("", self.config.port), handler_class)
            self._server.timeout = 1.0  # Allow periodic shutdown checks

            self._shutdown_event.clear()
            self._thread = threading.Thread(
                target=self._serve_forever,
                name="api-server",
                daemon=True,
            )
            self._thread.start()

            logger.info("API server started on port %d", self.config.port)

        except OSError as e:
            raise ApiError(f"Failed to start API server: {e}")

    def _serve_forever(self) -> None:
        """Server loop that checks for shutdown."""
        while not self._shutdown_event.is_set():
            if self._server:
                self._server.handle_request()

    def stop(self) -> None:
        """Stop the API server gracefully."""
        if self._thread is None:
            return

        logger.info("Stopping API server...")
        self._shutdown_event.set()

        if self._server:
            self._server.server_close()

        if self._thread.is_alive():
            self._thread.join(timeout=5.0)

        self._server = None
        self._thread = None
        logger.info("API server stopped")

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._thread is not None and self._thread.is_alive()
