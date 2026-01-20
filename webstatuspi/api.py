"""HTTP API server for URL monitoring status."""

import json
import logging
import sqlite3
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional

from .config import ApiConfig
from .database import (
    get_history,
    get_latest_status,
    get_latest_status_by_name,
    delete_all_checks,
    DatabaseError,
)
from .models import UrlStatus
from ._dashboard import HTML_DASHBOARD

logger = logging.getLogger(__name__)

# Rate limiting configuration.
# Allows 60 requests per minute per IP, sufficient for normal dashboard
# refresh cycles while protecting against DoS attacks.
RATE_LIMIT_MAX_REQUESTS = 60
RATE_LIMIT_WINDOW_SECONDS = 60

# Maximum number of history records to return per request.
# Balances memory usage vs useful data for 24-hour view at typical intervals.
HISTORY_LIMIT = 100


class RateLimiter:
    """Simple sliding window rate limiter by IP address.

    Allows up to max_requests requests per IP within the time window.
    Thread-safe for use in multi-threaded HTTP server.
    """

    def __init__(
        self,
        max_requests: int = RATE_LIMIT_MAX_REQUESTS,
        window_seconds: int = RATE_LIMIT_WINDOW_SECONDS,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, client_ip: str) -> bool:
        """Check if a request from the given IP is allowed.

        Args:
            client_ip: The client's IP address.

        Returns:
            True if the request is allowed, False if rate limited.
        """
        now = time.monotonic()
        cutoff = now - self._window_seconds

        with self._lock:
            # Clean old entries and get current request timestamps
            timestamps = self._requests[client_ip]
            timestamps[:] = [ts for ts in timestamps if ts > cutoff]

            if len(timestamps) >= self._max_requests:
                return False

            timestamps.append(now)
            return True

    def cleanup(self) -> None:
        """Remove stale entries from the rate limiter."""
        now = time.monotonic()
        cutoff = now - self._window_seconds

        with self._lock:
            empty_ips = []
            for ip, timestamps in self._requests.items():
                timestamps[:] = [ts for ts in timestamps if ts > cutoff]
                if not timestamps:
                    empty_ips.append(ip)
            for ip in empty_ips:
                del self._requests[ip]


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

    # Class-level references set by factory
    db_conn: Optional[sqlite3.Connection] = None
    reset_token: Optional[str] = None  # Required for DELETE /reset when set
    rate_limiter: Optional[RateLimiter] = None

    # Headers that indicate traffic is coming through Cloudflare
    CLOUDFLARE_HEADERS = ("CF-Connecting-IP", "CF-Ray", "CF-IPCountry")

    def _is_cloudflare_request(self) -> bool:
        """Check if the request is coming through Cloudflare.

        Cloudflare adds specific headers to all proxied requests.
        If any of these headers are present, the request is from Cloudflare.
        """
        for header in self.CLOUDFLARE_HEADERS:
            if self.headers.get(header):
                return True
        return False

    def log_message(self, format: str, *args: Any) -> None:
        """Override to use Python logging instead of stderr."""
        logger.debug("API %s - %s", self.address_string(), format % args)

    def _check_rate_limit(self) -> bool:
        """Check if the request should be rate limited.

        Returns:
            True if request is allowed, False if rate limited.
            Sends 429 response automatically if rate limited.
        """
        if self.rate_limiter is None:
            return True

        client_ip = self.client_address[0]
        if not self.rate_limiter.is_allowed(client_ip):
            logger.warning("Rate limit exceeded for %s", client_ip)
            self._send_error_json(429, "Rate limit exceeded. Try again later.")
            return False
        return True

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
        if not self._check_rate_limit():
            return

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

    def do_DELETE(self) -> None:
        """Handle DELETE requests."""
        if not self._check_rate_limit():
            return

        try:
            if self.path == "/reset":
                self._handle_reset()
            else:
                self._send_error_json(404, "Not found")
        except Exception as e:
            logger.exception("Error handling DELETE request: %s", e)
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
            # Use efficient single-URL query instead of fetching all
            status = get_latest_status_by_name(self.db_conn, name)

            if status is None:
                self._send_error_json(404, f"URL '{name}' not found")
                return

            response = _url_status_to_dict(status)
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
            # First check if the URL exists using efficient single-URL query
            status = get_latest_status_by_name(self.db_conn, name)

            if status is None:
                self._send_error_json(404, f"URL '{name}' not found")
                return

            # Get history for the last 24 hours
            since = datetime.utcnow() - timedelta(hours=24)
            checks = get_history(self.db_conn, name, since, limit=HISTORY_LIMIT)

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

    def _handle_reset(self) -> None:
        """Handle DELETE /reset endpoint - delete all check records.

        Only allowed from local network (not through Cloudflare).
        If reset_token is configured, requires Authorization header with
        'Bearer <token>' format.
        """
        # Block requests coming through Cloudflare (external access)
        if self._is_cloudflare_request():
            logger.warning("Reset attempt blocked from Cloudflare: %s", self.address_string())
            self._send_error_json(403, "Nice try, Diddy! You are not allowed to perform this action")
            return

        if self.db_conn is None:
            self._send_error_json(503, "Database not available")
            return

        # Check authentication if reset_token is configured
        if self.reset_token is not None:
            auth_header = self.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                self._send_error_json(401, "Authorization required: Bearer token expected")
                return
            provided_token = auth_header[7:]  # Strip "Bearer "
            if provided_token != self.reset_token:
                logger.warning("Invalid reset token attempt from %s", self.address_string())
                self._send_error_json(403, "Invalid reset token")
                return

        try:
            deleted = delete_all_checks(self.db_conn)
            logger.info("Reset data: deleted %d check records", deleted)
            self._send_json(200, {"success": True, "deleted": deleted})
        except DatabaseError as e:
            logger.error("Database error in /reset: %s", e)
            self._send_error_json(500, "Database error")


def _create_handler_class(
    db_conn: sqlite3.Connection,
    reset_token: Optional[str] = None,
    rate_limiter: Optional[RateLimiter] = None,
) -> type:
    """Create a handler class with the database connection and config bound."""

    class BoundStatusHandler(StatusHandler):
        pass

    BoundStatusHandler.db_conn = db_conn
    BoundStatusHandler.reset_token = reset_token
    BoundStatusHandler.rate_limiter = rate_limiter
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
        self._rate_limiter = RateLimiter()

    def start(self) -> None:
        """Start the API server in a background thread.

        Raises:
            ApiError: If the server fails to start.
        """
        if self._thread is not None and self._thread.is_alive():
            logger.warning("API server is already running")
            return

        try:
            handler_class = _create_handler_class(
                self.db_conn,
                self.config.reset_token,
                self._rate_limiter,
            )
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
            # Provide specific guidance based on error type
            if e.errno == 98 or e.errno == 48:  # EADDRINUSE (Linux=98, macOS=48)
                raise ApiError(
                    f"Port {self.config.port} is already in use. "
                    f"Another process may be using this port, or webstatuspi is already running."
                )
            elif e.errno == 13:  # EACCES - Permission denied
                raise ApiError(
                    f"Permission denied for port {self.config.port}. "
                    f"Ports below 1024 require root privileges. "
                    f"Use a port >= 1024 or run with elevated permissions."
                )
            else:
                raise ApiError(f"Failed to start API server on port {self.config.port}: {e}")

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
