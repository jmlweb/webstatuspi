"""HTTP API server for URL monitoring status."""

import ipaddress
import json
import logging
import secrets
import sqlite3
import threading
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import unquote

from ._dashboard import (
    CSP_NONCE_PLACEHOLDER,
    HTML_DASHBOARD,
)
from ._pwa import (
    ICON_192_PNG,
    ICON_512_PNG,
    MANIFEST_JSON,
    SERVICE_WORKER_JS,
)
from .config import ApiConfig
from .database import (
    DatabaseError,
    delete_all_checks,
    get_history,
    get_latest_status,
    get_latest_status_by_name,
)
from .models import UrlStatus

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
        self._requests: dict[str, list[float]] = defaultdict(list)
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


def _url_status_to_dict(status: UrlStatus) -> dict[str, Any]:
    """Convert a UrlStatus object to a JSON-serializable dictionary."""
    return {
        "name": status.url_name,
        "url": status.url,
        "is_up": status.is_up,
        "status_code": status.last_status_code,
        "response_time_ms": status.last_response_time_ms,
        "error": status.last_error,
        "last_check": status.last_check.isoformat().replace("+00:00", "Z"),
        "checks_24h": status.checks_24h,
        "uptime_24h": round(status.uptime_24h, 2),
        "avg_response_time_24h": round(status.avg_response_time_24h, 2)
        if status.avg_response_time_24h is not None
        else None,
        "min_response_time_24h": status.min_response_time_24h,
        "max_response_time_24h": status.max_response_time_24h,
        "consecutive_failures": status.consecutive_failures,
        "last_downtime": status.last_downtime.isoformat().replace("+00:00", "Z")
        if status.last_downtime is not None
        else None,
        "content_length": status.content_length,
        "server_header": status.server_header,
        "status_text": status.status_text,
        "p50_response_time_24h": status.p50_response_time_24h,
        "p95_response_time_24h": status.p95_response_time_24h,
        "p99_response_time_24h": status.p99_response_time_24h,
        "stddev_response_time_24h": round(status.stddev_response_time_24h, 2)
        if status.stddev_response_time_24h is not None
        else None,
    }


def _build_status_response(statuses: list[UrlStatus], internet_status: bool | None = None) -> dict[str, Any]:
    """Build the full status response with summary.

    Args:
        statuses: List of URL statuses to include in the response.
        internet_status: Current internet connectivity status (None if unknown,
                        True if available, False if no internet detected).
    """
    urls_data = [_url_status_to_dict(s) for s in statuses]
    up_count = sum(1 for s in statuses if s.is_up)

    response: dict[str, Any] = {
        "urls": urls_data,
        "summary": {
            "total": len(statuses),
            "up": up_count,
            "down": len(statuses) - up_count,
        },
    }

    if internet_status is not None:
        response["internet_status"] = internet_status

    return response


def _format_prometheus_metrics(statuses: list[UrlStatus]) -> str:
    """Format URL statuses as Prometheus text format metrics.

    Prometheus text format: https://prometheus.io/docs/instrumenting/exposition_formats/
    Format: metric_name{label="value"} value timestamp

    Args:
        statuses: List of URL statuses to convert to metrics.

    Returns:
        Prometheus text format metrics string.
    """
    lines = []

    # webstatuspi_uptime_percentage
    lines.append("# HELP webstatuspi_uptime_percentage Uptime percentage for the last 24 hours")
    lines.append("# TYPE webstatuspi_uptime_percentage gauge")
    for status in statuses:
        # Escape label values (replace " with \", \ with \\, newline with \n)
        url_name = status.url_name.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        url = status.url.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        lines.append(f'webstatuspi_uptime_percentage{{url_name="{url_name}",url="{url}"}} {status.uptime_24h}')

    # webstatuspi_response_time_ms (avg, min, max)
    lines.append("")
    lines.append("# HELP webstatuspi_response_time_ms Response time metrics in milliseconds")
    lines.append("# TYPE webstatuspi_response_time_ms gauge")
    for status in statuses:
        url_name = status.url_name.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        url = status.url.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

        if status.avg_response_time_24h is not None:
            lines.append(
                f'webstatuspi_response_time_ms{{url_name="{url_name}",url="{url}",type="avg"}} '
                f"{status.avg_response_time_24h}"
            )
        if status.min_response_time_24h is not None:
            lines.append(
                f'webstatuspi_response_time_ms{{url_name="{url_name}",url="{url}",type="min"}} '
                f"{status.min_response_time_24h}"
            )
        if status.max_response_time_24h is not None:
            lines.append(
                f'webstatuspi_response_time_ms{{url_name="{url_name}",url="{url}",type="max"}} '
                f"{status.max_response_time_24h}"
            )

    # webstatuspi_checks_total (success, failure)
    lines.append("")
    lines.append("# HELP webstatuspi_checks_total Total number of checks performed")
    lines.append("# TYPE webstatuspi_checks_total counter")
    for status in statuses:
        url_name = status.url_name.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        url = status.url.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

        # Calculate success and failure counts from uptime percentage
        success_count = int(status.checks_24h * (status.uptime_24h / 100.0))
        failure_count = status.checks_24h - success_count

        lines.append(f'webstatuspi_checks_total{{url_name="{url_name}",url="{url}",status="success"}} {success_count}')
        lines.append(f'webstatuspi_checks_total{{url_name="{url_name}",url="{url}",status="failure"}} {failure_count}')

    # webstatuspi_last_check_timestamp
    lines.append("")
    lines.append("# HELP webstatuspi_last_check_timestamp Unix timestamp of last check")
    lines.append("# TYPE webstatuspi_last_check_timestamp gauge")
    for status in statuses:
        url_name = status.url_name.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        url = status.url.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        timestamp = int(status.last_check.timestamp())
        lines.append(f'webstatuspi_last_check_timestamp{{url_name="{url_name}",url="{url}"}} {timestamp}')

    return "\n".join(lines) + "\n"


class StatusHandler(BaseHTTPRequestHandler):
    """HTTP request handler for status API endpoints."""

    # Class-level references set by factory
    db_conn: sqlite3.Connection | None = None
    reset_token: str | None = None  # Required for DELETE /reset when set
    rate_limiter: RateLimiter | None = None
    internet_status_getter: Any | None = None  # Callable that returns bool | None
    _request_count: int = 0  # Counter for periodic rate limiter cleanup
    _cleanup_lock = threading.Lock()  # Lock for thread-safe cleanup counter

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

    def _get_client_ip(self) -> str:
        """Get the real client IP, considering proxies like Cloudflare.

        When behind Cloudflare, the socket IP is Cloudflare's server IP.
        The real client IP is in the CF-Connecting-IP header.

        Returns:
            The client's real IP address.
        """
        # Only trust CF-Connecting-IP if this is actually a Cloudflare request
        if self._is_cloudflare_request():
            cf_ip = self.headers.get("CF-Connecting-IP")
            if cf_ip:
                # Validate IP format to prevent header injection
                try:
                    ipaddress.ip_address(cf_ip.strip())
                    return cf_ip.strip()
                except ValueError:
                    logger.warning("Invalid CF-Connecting-IP header: %s", cf_ip)

        # Fallback to socket IP (direct connection or untrusted proxy)
        return self.client_address[0]

    def _check_rate_limit(self) -> bool:
        """Check if the request should be rate limited.

        Returns:
            True if request is allowed, False if rate limited.
            Sends 429 response automatically if rate limited.
        """
        if self.rate_limiter is None:
            return True

        client_ip = self._get_client_ip()

        # Skip rate limiting for local/loopback addresses
        try:
            ip = ipaddress.ip_address(client_ip)
            if ip.is_loopback or ip.is_private:
                return True
        except ValueError:
            # Invalid IP format, proceed with rate limiting
            pass

        if not self.rate_limiter.is_allowed(client_ip):
            logger.warning("Rate limit exceeded for %s", client_ip)
            self._send_error_json(429, "Rate limit exceeded. Try again later.")
            return False
        return True

    def _maybe_cleanup_rate_limiter(self) -> None:
        """Periodically cleanup rate limiter to prevent memory leak."""
        if self.rate_limiter is None:
            return

        # Cleanup every 100 requests to prevent unbounded memory growth
        with self._cleanup_lock:
            self._request_count += 1
            if self._request_count >= 100:
                self.rate_limiter.cleanup()
                self._request_count = 0

    def _add_security_headers(self, nonce: str | None = None) -> None:
        """Add security headers to the current response.

        Args:
            nonce: Optional CSP nonce for inline scripts/styles.
                   If provided, uses nonce-based CSP instead of 'unsafe-inline'.
        """
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-XSS-Protection", "1; mode=block")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")

        # Build CSP based on whether nonce is provided
        if nonce:
            # Nonce-based CSP (more secure) - used for dashboard
            csp = (
                f"default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}'; "
                f"style-src 'self' 'nonce-{nonce}' 'unsafe-inline' https://fonts.googleapis.com; "
                f"font-src 'self' https://fonts.gstatic.com; "
                f"img-src 'self' data:; "
                f"connect-src 'self'; "
                f"object-src 'none'; "
                f"base-uri 'self'; "
                f"form-action 'self'; "
                f"frame-ancestors 'none';"
            )
        else:
            # Basic CSP for API endpoints (no inline content)
            csp = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "font-src 'self'; "
                "img-src 'self'; "
                "connect-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none';"
            )

        self.send_header("Content-Security-Policy", csp)

    def _validate_url_name(self, name: str) -> str | None:
        """Validate and sanitize URL name from path parameter.

        Args:
            name: Raw URL name from path

        Returns:
            Validated name if safe, None if invalid
        """
        if not name:
            return None

        # URL decode to handle encoded sequences
        try:
            decoded = unquote(name)
        except Exception:
            return None

        # Reject path traversal sequences
        if ".." in decoded or "/" in decoded or "\\" in decoded:
            return None

        # Reject null bytes and control characters
        if "\x00" in decoded or any(ord(c) < 32 and c not in "\t\n\r" for c in decoded):
            return None

        # URL names are limited to 10 chars and alphanumeric/underscore in config
        # But we validate here too for safety
        if len(decoded) > 10:
            return None

        return decoded

    def _send_json(self, code: int, data: dict[str, Any]) -> None:
        """Send a JSON response with the given status code."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self._add_security_headers()
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
        self._add_security_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _send_html_bytes(self, code: int, body: bytes, nonce: str | None = None) -> None:
        """Send an HTML response with pre-encoded bytes.

        More efficient than _send_html() when the body is already encoded.

        Args:
            code: HTTP status code.
            body: Pre-encoded HTML body.
            nonce: Optional CSP nonce for inline scripts/styles.
        """
        self.send_response(code)
        self._add_security_headers(nonce)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # Cache-Control: no-cache for real-time dashboard, but allow private caching
        self.send_header("Cache-Control", "private, no-cache, must-revalidate")
        # Hint to browser to prefetch DNS for external resources
        self.send_header("X-DNS-Prefetch-Control", "on")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _send_manifest(self, manifest: str) -> None:
        """Send the PWA manifest JSON."""
        body = manifest.encode("utf-8")
        self.send_response(200)
        self._add_security_headers()
        self.send_header("Content-Type", "application/manifest+json")
        self.send_header("Content-Length", str(len(body)))
        # Cache manifest for 1 hour (will be invalidated by SW version change)
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _send_service_worker(self, sw_js: str) -> None:
        """Send the Service Worker JavaScript.

        Service Workers must not be cached by the browser to enable updates.
        The browser will byte-compare the SW on each registration.update().
        """
        body = sw_js.encode("utf-8")
        self.send_response(200)
        self._add_security_headers()
        self.send_header("Content-Type", "application/javascript")
        self.send_header("Content-Length", str(len(body)))
        # SW must not be cached - browser handles update detection
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _send_png(self, png_data: bytes) -> None:
        """Send a PNG image (for PWA icons)."""
        self.send_response(200)
        self._add_security_headers()
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(png_data)))
        # Cache icons for 1 week (immutable, versioned via manifest)
        self.send_header("Cache-Control", "public, max-age=604800, immutable")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(png_data)

    def _send_text(self, code: int, text: str, content_type: str = "text/plain") -> None:
        """Send a plain text response with the given status code.

        Args:
            code: HTTP status code.
            text: Plain text content.
            content_type: Content-Type header value.
        """
        body = text.encode("utf-8")
        self.send_response(code)
        self._add_security_headers()
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
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
                name = self._validate_url_name(self.path[8:])  # Extract name after /status/
                if name:
                    self._handle_status_by_name(name)
                else:
                    self._send_error_json(400, "Invalid URL name")
            elif self.path.startswith("/history/"):
                name = self._validate_url_name(self.path[9:])  # Extract name after /history/
                if name:
                    self._handle_history_by_name(name)
                else:
                    self._send_error_json(400, "Invalid URL name")
            elif self.path == "/metrics":
                self._handle_metrics()
            # PWA endpoints
            elif self.path == "/manifest.json":
                self._send_manifest(MANIFEST_JSON)
            elif self.path == "/sw.js":
                self._send_service_worker(SERVICE_WORKER_JS)
            elif self.path == "/icon-192.png":
                self._send_png(ICON_192_PNG)
            elif self.path == "/icon-512.png":
                self._send_png(ICON_512_PNG)
            else:
                self._send_error_json(404, "Not found")
        except Exception as e:
            logger.exception("Error handling request: %s", e)
            self._send_error_json(500, "Internal server error")
        finally:
            self._maybe_cleanup_rate_limiter()

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
        finally:
            self._maybe_cleanup_rate_limiter()

    def _handle_dashboard(self) -> None:
        """Handle GET / endpoint - serve HTML dashboard with initial data."""
        # Generate CSP nonce for this request
        nonce = secrets.token_urlsafe(16)

        # Inject initial data for SSR
        if self.db_conn is not None:
            try:
                statuses = get_latest_status(self.db_conn)
                internet_status = self.internet_status_getter() if self.internet_status_getter else None
                response = _build_status_response(statuses, internet_status)
                initial_data = json.dumps(response)
            except DatabaseError:
                initial_data = "null"
        else:
            initial_data = "null"

        # Build HTML with nonce and initial data injected
        # Replace nonce placeholder in the template, then inject data
        html = HTML_DASHBOARD.replace(CSP_NONCE_PLACEHOLDER, nonce)
        html = html.replace("__INITIAL_DATA__", initial_data)
        body = html.encode("utf-8")

        self._send_html_bytes(200, body, nonce)

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
            internet_status = self.internet_status_getter() if self.internet_status_getter else None
            response = _build_status_response(statuses, internet_status)
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
            since = datetime.now(UTC) - timedelta(hours=24)
            checks = get_history(self.db_conn, name, since, limit=HISTORY_LIMIT)

            response = {
                "name": name,
                "checks": [
                    {
                        "checked_at": c.checked_at.isoformat().replace("+00:00", "Z"),
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

    def _handle_metrics(self) -> None:
        """Handle GET /metrics endpoint - Prometheus text format metrics."""
        if self.db_conn is None:
            self._send_error_json(503, "Database not available")
            return

        try:
            statuses = get_latest_status(self.db_conn)
            metrics = _format_prometheus_metrics(statuses)
            self._send_text(200, metrics, "text/plain; version=0.0.4")
        except DatabaseError as e:
            logger.error("Database error in /metrics: %s", e)
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
            if not secrets.compare_digest(provided_token, self.reset_token):
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
    reset_token: str | None = None,
    rate_limiter: RateLimiter | None = None,
    internet_status_getter: Any | None = None,
) -> type:
    """Create a handler class with the database connection and config bound.

    Args:
        db_conn: Database connection for querying status.
        reset_token: Optional token for authenticating DELETE /reset requests.
        rate_limiter: Optional rate limiter for protecting against DoS.
        internet_status_getter: Optional callable that returns current internet status.
    """

    class BoundStatusHandler(StatusHandler):
        pass

    BoundStatusHandler.db_conn = db_conn
    BoundStatusHandler.reset_token = reset_token
    BoundStatusHandler.rate_limiter = rate_limiter
    BoundStatusHandler.internet_status_getter = internet_status_getter
    return BoundStatusHandler


class ApiServer:
    """Threaded HTTP API server for URL monitoring status."""

    def __init__(
        self,
        config: ApiConfig,
        db_conn: sqlite3.Connection,
        internet_status_getter: Any | None = None,
    ) -> None:
        """Initialize the API server.

        Args:
            config: API configuration.
            db_conn: Database connection for querying status.
            internet_status_getter: Optional callable that returns current internet status.
        """
        self.config = config
        self.db_conn = db_conn
        self.internet_status_getter = internet_status_getter
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
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
                self.internet_status_getter,
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
