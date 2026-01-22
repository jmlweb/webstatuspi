"""URL monitoring loop with threaded health checks."""

import json
import logging
import socket
import sqlite3
import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Event, Thread
from urllib.parse import urlparse

from .config import Config, DnsConfig, TargetConfig, TcpConfig, UrlConfig
from .database import cleanup_old_checks, insert_check
from .models import CheckResult
from .security import SSRFError, validate_url_for_ssrf

logger = logging.getLogger(__name__)


class _RedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom redirect handler that follows 307 and 308 redirects."""

    def http_error_307(self, req, fp, code, msg, headers):
        """Handle 307 Temporary Redirect."""
        return self._do_redirect(req, fp, code, msg, headers)

    def http_error_308(self, req, fp, code, msg, headers):
        """Handle 308 Permanent Redirect."""
        return self._do_redirect(req, fp, code, msg, headers)

    def _do_redirect(self, req, fp, code, msg, headers):
        """Follow redirect preserving the original method."""
        new_url = headers.get("Location")
        if new_url:
            new_req = urllib.request.Request(
                new_url,
                method=req.get_method(),
                headers=dict(req.headers),
            )
            return self.parent.open(new_req, timeout=req.timeout)
        return None


# Create opener with custom redirect handler
_opener = urllib.request.build_opener(_RedirectHandler())

# Pi 1B+ optimized: limit concurrent checks to avoid resource contention.
# Three workers balances parallel checks vs memory/CPU on constrained hardware.
MAX_WORKERS = 3

# Run cleanup every N check cycles to minimize SD card writes.
# At 60s interval, this means cleanup runs roughly every ~100 minutes.
CLEANUP_INTERVAL_CYCLES = 100

# Timeout for internet connectivity check in seconds.
# Reduced from 5s to avoid blocking the check cycle too long on Pi 1B+.
INTERNET_CHECK_TIMEOUT = 3

# Cache duration for internet connectivity status in seconds.
# Prevents repeated blocking DNS checks when internet is down.
CONNECTIVITY_CACHE_SECONDS = 30

# Maximum response body size to read for content validation (1MB).
# Pi 1B+ memory constraint: prevent loading large responses into memory.
MAX_BODY_SIZE = 1024 * 1024  # 1MB

# Default warning threshold for SSL certificate expiration (days).
DEFAULT_SSL_WARNING_DAYS = 30


def _is_success_status(status_code: int, success_codes: list[int | tuple[int, int]] | None) -> bool:
    """Check if a status code indicates success.

    Args:
        status_code: HTTP status code to check.
        success_codes: Custom success codes (ints or (start, end) tuples), or None for default.

    Returns:
        True if status code indicates success, False otherwise.
    """
    if success_codes is None:
        # Default: 2xx and 3xx are success
        return 200 <= status_code < 400

    for code in success_codes:
        if isinstance(code, int):
            if status_code == code:
                return True
        elif isinstance(code, tuple):
            start, end = code
            if start <= status_code <= end:
                return True
    return False


@dataclass(frozen=True)
class SSLCertInfo:
    """SSL certificate information extracted from an HTTPS URL.

    Attributes:
        issuer: Certificate issuer organization name.
        subject: Certificate subject common name.
        expires_at: Certificate expiration timestamp (UTC).
        expires_in_days: Days until expiration (negative if expired).
    """

    issuer: str | None
    subject: str | None
    expires_at: datetime
    expires_in_days: int


def _get_ssl_cert_info(url: str, timeout: int) -> tuple[SSLCertInfo | None, str | None]:
    """Extract SSL certificate information from an HTTPS URL.

    Uses a separate SSL connection (not urllib) to get the raw certificate data,
    since urllib doesn't expose certificate details reliably.

    Args:
        url: The URL to check (must be HTTPS).
        timeout: Connection timeout in seconds.

    Returns:
        Tuple of (SSLCertInfo, None) on success, or (None, error_message) on failure.
    """
    parsed = urlparse(url)

    # Only HTTPS URLs have SSL certificates
    if parsed.scheme != "https":
        return None, None

    hostname = parsed.hostname
    port = parsed.port or 443

    if not hostname:
        return None, "Invalid URL: no hostname"

    try:
        # Create SSL context with default CA certificates
        context = ssl.create_default_context()

        # Connect and get certificate
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssl_sock:
                cert = ssl_sock.getpeercert()

        if not cert:
            return None, "No certificate returned by server"

        # Extract expiration date (notAfter is in format: 'Mon DD HH:MM:SS YYYY GMT')
        not_after_raw = cert.get("notAfter")
        if not not_after_raw or not isinstance(not_after_raw, str):
            return None, "Certificate missing expiration date"

        # Parse the certificate date format
        expires_at = datetime.strptime(not_after_raw, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)

        # Calculate days until expiration
        now = datetime.now(UTC)
        delta = expires_at - now
        expires_in_days = delta.days

        # Extract issuer organization name
        issuer: str | None = None
        issuer_tuple = cert.get("issuer", ())
        if isinstance(issuer_tuple, tuple):
            issuer_dict: dict[str, str] = {}
            for item in issuer_tuple:
                if isinstance(item, tuple) and len(item) > 0:
                    first = item[0]
                    if isinstance(first, tuple) and len(first) == 2:
                        issuer_dict[str(first[0])] = str(first[1])
            issuer = issuer_dict.get("organizationName") or issuer_dict.get("commonName")

        # Extract subject common name
        subject: str | None = None
        subject_tuple = cert.get("subject", ())
        if isinstance(subject_tuple, tuple):
            subject_dict: dict[str, str] = {}
            for item in subject_tuple:
                if isinstance(item, tuple) and len(item) > 0:
                    first = item[0]
                    if isinstance(first, tuple) and len(first) == 2:
                        subject_dict[str(first[0])] = str(first[1])
            subject = subject_dict.get("commonName")

        return SSLCertInfo(
            issuer=issuer,
            subject=subject,
            expires_at=expires_at,
            expires_in_days=expires_in_days,
        ), None

    except ssl.SSLCertVerificationError as e:
        return None, f"SSL certificate verification failed: {e}"
    except ssl.SSLError as e:
        return None, f"SSL error: {e}"
    except TimeoutError:
        return None, "SSL connection timeout"
    except socket.gaierror as e:
        return None, f"DNS resolution failed: {e}"
    except OSError as e:
        return None, f"Connection failed: {e}"
    except Exception as e:
        return None, f"SSL check failed: {e}"


class _ConnectivityCache:
    """Simple cache for internet connectivity status.

    Avoids repeated blocking DNS checks when internet is down.
    """

    def __init__(self, cache_seconds: int = CONNECTIVITY_CACHE_SECONDS):
        self._cache_seconds = cache_seconds
        self._last_check_time: float | None = None
        self._cached_result: bool | None = None

    def get_cached(self) -> bool | None:
        """Get cached connectivity status if still valid.

        Returns:
            Cached bool result if cache is valid, None if cache expired or empty.
        """
        if self._last_check_time is None:
            return None
        if time.monotonic() - self._last_check_time > self._cache_seconds:
            return None
        return self._cached_result

    def update(self, is_connected: bool) -> None:
        """Update the cached connectivity status."""
        self._last_check_time = time.monotonic()
        self._cached_result = is_connected

    def invalidate(self) -> None:
        """Invalidate the cache when at least one URL succeeds."""
        self._last_check_time = None
        self._cached_result = None


# Global connectivity cache instance
_connectivity_cache = _ConnectivityCache()


def _validate_keyword(body: str, keyword: str) -> tuple[bool, str | None]:
    """Validate that response body contains the expected keyword.

    Args:
        body: Response body text.
        keyword: Expected keyword to find in body (case-sensitive).

    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.
    """
    if keyword in body:
        return True, None
    return False, f"Keyword '{keyword}' not found in response body"


def _validate_json_path(body: str, json_path: str) -> tuple[bool, str | None]:
    """Validate that JSON response contains expected value at path.

    Supports simple dot-notation paths like "status.healthy" or "data.success".
    Expects the final value to be truthy (true, "ok", "healthy", etc.).

    Args:
        body: Response body text (should be JSON).
        json_path: Dot-separated path to check (e.g., "status.healthy").

    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.
    """
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        return False, f"JSON validation failed: invalid JSON response ({e})"

    # Navigate the path
    keys = json_path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return False, f"JSON validation failed: path '{json_path}' not found (not a dict at '{key}')"
        if key not in current:
            return False, f"JSON validation failed: path '{json_path}' not found (missing key '{key}')"
        current = current[key]

    # Check if final value is truthy
    # Accept: true, "ok", "healthy", "success", 1, etc.
    # Reject: false, null, 0, empty string
    if not current:
        return False, f"JSON validation failed: path '{json_path}' has falsy value: {current!r}"

    return True, None


def check_internet_connectivity(
    timeout: int = INTERNET_CHECK_TIMEOUT,
    use_cache: bool = True,
) -> bool:
    """Check if internet connectivity is available via DNS lookup.

    Uses socket (stdlib) to avoid additional dependencies.
    Attempts TCP connection to Google's DNS server (8.8.8.8) on port 53.

    Results are cached for CONNECTIVITY_CACHE_SECONDS to avoid repeated
    blocking checks when internet is down.

    Args:
        timeout: Timeout in seconds for connectivity check.
        use_cache: Whether to use cached result if available.

    Returns:
        True if internet connectivity is available, False otherwise.
    """
    # Check cache first
    if use_cache:
        cached = _connectivity_cache.get_cached()
        if cached is not None:
            return cached

    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        result = True
    except (TimeoutError, OSError):
        result = False

    _connectivity_cache.update(result)
    return result


def check_url(
    url_config: UrlConfig,
    allow_private: bool = False,
    ssl_warning_days: int = DEFAULT_SSL_WARNING_DAYS,
) -> CheckResult:
    """Perform a single HTTP health check on a URL.

    Args:
        url_config: Configuration for the URL to check.
        allow_private: If True, allow private IPs (for testing only).
        ssl_warning_days: Days before expiration to log SSL certificate warnings.

    Returns:
        CheckResult with status, response time, and any error details.
    """
    start = time.monotonic()
    checked_at = datetime.now(UTC)

    # SSRF protection: validate URL before making request
    try:
        validate_url_for_ssrf(url_config.url, allow_private=allow_private)
    except SSRFError as e:
        logger.warning("SSRF validation failed for %s: %s", url_config.name, e)
        return CheckResult(
            url_name=url_config.name,
            url=url_config.url,
            status_code=None,
            response_time_ms=0,
            is_up=False,
            error_message=f"URL blocked: {e}",
            checked_at=checked_at,
        )

    # Extract SSL certificate info for HTTPS URLs (separate connection)
    # This happens before the HTTP check so SSL failures don't affect HTTP status
    ssl_cert_info: SSLCertInfo | None = None
    ssl_cert_error: str | None = None
    ssl_expired = False
    ssl_error_message: str | None = None

    if url_config.url.startswith("https://"):
        ssl_cert_info, ssl_cert_error = _get_ssl_cert_info(url_config.url, url_config.timeout)

        if ssl_cert_error:
            logger.debug("SSL cert extraction failed for %s: %s", url_config.name, ssl_cert_error)
        elif ssl_cert_info:
            # Check if certificate is expired
            if ssl_cert_info.expires_in_days < 0:
                ssl_expired = True
                ssl_error_message = f"SSL certificate expired {-ssl_cert_info.expires_in_days} days ago"
                logger.warning("%s: %s", url_config.name, ssl_error_message)
            elif ssl_cert_info.expires_in_days <= ssl_warning_days:
                logger.warning(
                    "%s: SSL certificate expires in %d days (threshold: %d)",
                    url_config.name,
                    ssl_cert_info.expires_in_days,
                    ssl_warning_days,
                )

    try:
        request = urllib.request.Request(
            url_config.url,
            method="GET",
            headers={"User-Agent": "WebStatusPi/0.1"},
        )
        with _opener.open(request, timeout=url_config.timeout) as response:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            status_code = response.status
            is_up = _is_success_status(status_code, url_config.success_codes)

            # Extract Content-Length header if present
            content_length_str = response.headers.get("Content-Length")
            content_length = int(content_length_str) if content_length_str else None

            # Extract Server header if present
            server_header = response.headers.get("Server")

            # Extract status text (reason phrase) if available
            status_text = getattr(response, "reason", None)

            # Perform content validation if configured
            error_message = None
            if is_up and (url_config.keyword or url_config.json_path):
                # Read response body (limited to MAX_BODY_SIZE for Pi 1B+ memory)
                body_bytes = response.read(MAX_BODY_SIZE)
                try:
                    body = body_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    is_up = False
                    error_message = "Content validation failed: response is not valid UTF-8"
                else:
                    # Keyword validation
                    if url_config.keyword:
                        is_valid, validation_error = _validate_keyword(body, url_config.keyword)
                        if not is_valid:
                            is_up = False
                            error_message = validation_error

                    # JSON path validation (only if keyword validation passed or not configured)
                    if is_up and url_config.json_path:
                        is_valid, validation_error = _validate_json_path(body, url_config.json_path)
                        if not is_valid:
                            is_up = False
                            error_message = validation_error

            # SSL expiration overrides is_up status
            if ssl_expired:
                is_up = False
                error_message = ssl_error_message

            return CheckResult(
                url_name=url_config.name,
                url=url_config.url,
                status_code=status_code,
                response_time_ms=elapsed_ms,
                is_up=is_up,
                error_message=error_message,
                checked_at=checked_at,
                content_length=content_length,
                server_header=server_header,
                status_text=status_text,
                ssl_cert_issuer=ssl_cert_info.issuer if ssl_cert_info else None,
                ssl_cert_subject=ssl_cert_info.subject if ssl_cert_info else None,
                ssl_cert_expires_at=ssl_cert_info.expires_at if ssl_cert_info else None,
                ssl_cert_expires_in_days=ssl_cert_info.expires_in_days if ssl_cert_info else None,
                ssl_cert_error=ssl_cert_error,
            )

    except urllib.error.HTTPError as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        # Use custom success codes or default (3xx redirects are "up")
        is_up = _is_success_status(e.code, url_config.success_codes)

        # Extract Content-Length header if present
        content_length_str = e.headers.get("Content-Length") if e.headers else None
        content_length = int(content_length_str) if content_length_str else None

        # Extract Server header if present
        server_header = e.headers.get("Server") if e.headers else None

        # Extract status text (reason phrase)
        status_text = getattr(e, "reason", None)

        # SSL expiration overrides is_up status
        error_message = None if is_up else f"HTTP {e.code}: {e.reason}"
        if ssl_expired:
            is_up = False
            error_message = ssl_error_message

        return CheckResult(
            url_name=url_config.name,
            url=url_config.url,
            status_code=e.code,
            response_time_ms=elapsed_ms,
            is_up=is_up,
            error_message=error_message,
            checked_at=checked_at,
            content_length=content_length,
            server_header=server_header,
            status_text=status_text,
            ssl_cert_issuer=ssl_cert_info.issuer if ssl_cert_info else None,
            ssl_cert_subject=ssl_cert_info.subject if ssl_cert_info else None,
            ssl_cert_expires_at=ssl_cert_info.expires_at if ssl_cert_info else None,
            ssl_cert_expires_in_days=ssl_cert_info.expires_in_days if ssl_cert_info else None,
            ssl_cert_error=ssl_cert_error,
        )

    except urllib.error.URLError as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        reason = str(e.reason) if e.reason else "Connection failed"
        return CheckResult(
            url_name=url_config.name,
            url=url_config.url,
            status_code=None,
            response_time_ms=elapsed_ms,
            is_up=False,
            error_message=ssl_error_message if ssl_expired else reason,
            checked_at=checked_at,
            ssl_cert_issuer=ssl_cert_info.issuer if ssl_cert_info else None,
            ssl_cert_subject=ssl_cert_info.subject if ssl_cert_info else None,
            ssl_cert_expires_at=ssl_cert_info.expires_at if ssl_cert_info else None,
            ssl_cert_expires_in_days=ssl_cert_info.expires_in_days if ssl_cert_info else None,
            ssl_cert_error=ssl_cert_error,
        )

    except Exception as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return CheckResult(
            url_name=url_config.name,
            url=url_config.url,
            status_code=None,
            response_time_ms=elapsed_ms,
            is_up=False,
            error_message=ssl_error_message if ssl_expired else str(e),
            checked_at=checked_at,
            ssl_cert_issuer=ssl_cert_info.issuer if ssl_cert_info else None,
            ssl_cert_subject=ssl_cert_info.subject if ssl_cert_info else None,
            ssl_cert_expires_at=ssl_cert_info.expires_at if ssl_cert_info else None,
            ssl_cert_expires_in_days=ssl_cert_info.expires_in_days if ssl_cert_info else None,
            ssl_cert_error=ssl_cert_error,
        )


def check_tcp(tcp_config: TcpConfig) -> CheckResult:
    """Perform a TCP connection check to a host:port.

    Attempts to establish a TCP connection and measures the connection time.
    Success is determined by whether the connection is established within
    the timeout period.

    Args:
        tcp_config: TCP target configuration (host, port, timeout).

    Returns:
        CheckResult with connection status and timing information.
    """
    checked_at = datetime.now(UTC)
    start = time.monotonic()

    try:
        sock = socket.create_connection(
            (tcp_config.host, tcp_config.port),
            timeout=tcp_config.timeout,
        )
        sock.close()
        elapsed_ms = int((time.monotonic() - start) * 1000)

        return CheckResult(
            url_name=tcp_config.name,
            url=tcp_config.url,  # tcp://host:port format
            status_code=None,  # No status code for TCP
            response_time_ms=elapsed_ms,
            is_up=True,
            error_message=None,
            checked_at=checked_at,
        )

    except TimeoutError:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return CheckResult(
            url_name=tcp_config.name,
            url=tcp_config.url,
            status_code=None,
            response_time_ms=elapsed_ms,
            is_up=False,
            error_message=f"Connection timeout after {tcp_config.timeout}s",
            checked_at=checked_at,
        )

    except OSError as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return CheckResult(
            url_name=tcp_config.name,
            url=tcp_config.url,
            status_code=None,
            response_time_ms=elapsed_ms,
            is_up=False,
            error_message=str(e),
            checked_at=checked_at,
        )

    except Exception as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return CheckResult(
            url_name=tcp_config.name,
            url=tcp_config.url,
            status_code=None,
            response_time_ms=elapsed_ms,
            is_up=False,
            error_message=str(e),
            checked_at=checked_at,
        )


def check_dns(dns_config: DnsConfig) -> CheckResult:
    """Perform a DNS resolution check for a hostname.

    Resolves the hostname and measures resolution time. Optionally verifies
    that the resolved IP matches an expected value.

    Args:
        dns_config: DNS target configuration (host, record_type, expected_ip).

    Returns:
        CheckResult with resolution status and timing information.
    """
    checked_at = datetime.now(UTC)
    start = time.monotonic()

    try:
        if dns_config.record_type == "A":
            # IPv4 resolution
            resolved_ip = socket.gethostbyname(dns_config.host)
        else:
            # AAAA (IPv6) resolution
            infos = socket.getaddrinfo(
                dns_config.host,
                None,
                socket.AF_INET6,
                socket.SOCK_STREAM,
            )
            if not infos:
                raise socket.gaierror(socket.EAI_NONAME, "No IPv6 address found")
            resolved_ip = str(infos[0][4][0])

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Check if resolved IP matches expected value
        if dns_config.expected_ip is not None and resolved_ip != dns_config.expected_ip:
            return CheckResult(
                url_name=dns_config.name,
                url=dns_config.url,
                status_code=None,
                response_time_ms=elapsed_ms,
                is_up=False,
                error_message=f"Resolved {resolved_ip} but expected {dns_config.expected_ip}",
                checked_at=checked_at,
            )

        return CheckResult(
            url_name=dns_config.name,
            url=dns_config.url,
            status_code=None,
            response_time_ms=elapsed_ms,
            is_up=True,
            error_message=None,
            checked_at=checked_at,
        )

    except socket.gaierror as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return CheckResult(
            url_name=dns_config.name,
            url=dns_config.url,
            status_code=None,
            response_time_ms=elapsed_ms,
            is_up=False,
            error_message=f"DNS resolution failed: {e}",
            checked_at=checked_at,
        )

    except TimeoutError:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return CheckResult(
            url_name=dns_config.name,
            url=dns_config.url,
            status_code=None,
            response_time_ms=elapsed_ms,
            is_up=False,
            error_message=f"DNS resolution timeout after {dns_config.timeout}s",
            checked_at=checked_at,
        )

    except Exception as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return CheckResult(
            url_name=dns_config.name,
            url=dns_config.url,
            status_code=None,
            response_time_ms=elapsed_ms,
            is_up=False,
            error_message=str(e),
            checked_at=checked_at,
        )


def check_target(target: TargetConfig, **kwargs) -> CheckResult:
    """Check a target (URL, TCP, or DNS) and return the result.

    Dispatcher function that routes to the appropriate check function
    based on target type.

    Args:
        target: Target configuration (UrlConfig, TcpConfig, or DnsConfig).
        **kwargs: Additional arguments passed to check_url (ssl_warning_days, allow_private).

    Returns:
        CheckResult with status and timing information.
    """
    if isinstance(target, TcpConfig):
        return check_tcp(target)
    elif isinstance(target, DnsConfig):
        return check_dns(target)
    else:
        return check_url(target, **kwargs)


class Monitor:
    """Threaded monitor that checks URLs, TCP, and DNS targets at a global interval.

    All targets are checked together at the configured monitor interval.
    Checks run concurrently using a thread pool, optimized for
    Raspberry Pi 1B+ constraints.

    Example:
        monitor = Monitor(config, db_conn)
        monitor.start()
        # ... later ...
        monitor.stop()
    """

    def __init__(
        self,
        config: Config,
        db_conn: sqlite3.Connection,
        on_check: Callable[[CheckResult], None] | None = None,
    ) -> None:
        """Initialize the monitor.

        Args:
            config: Application configuration with targets to monitor.
            db_conn: Database connection for storing results.
            on_check: Optional callback invoked after each check completes.
        """
        self._config = config
        self._db_conn = db_conn
        self._on_check = on_check
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._cycle_count = 0

        # Internet connectivity status: None (unknown), True (available), False (no internet)
        self._internet_status: bool | None = None

        # Track next check time for each target (staggered start)
        self._next_check: dict[str, float] = {}
        now = time.monotonic()
        for i, target in enumerate(config.all_targets):
            # Stagger initial checks by 2 seconds each to avoid burst
            self._next_check[target.name] = now + (i * 2)

    def start(self) -> None:
        """Start the monitor loop in a background thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Monitor already running")
            return

        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, daemon=True, name="monitor-loop")
        self._thread.start()
        logger.info(
            "Monitor started with %d URLs, %d TCP, and %d DNS targets",
            len(self._config.urls),
            len(self._config.tcp),
            len(self._config.dns),
        )

    def stop(self, timeout: float = 10.0) -> None:
        """Stop the monitor loop gracefully.

        Args:
            timeout: Maximum seconds to wait for the loop to stop.
        """
        if self._thread is None or not self._thread.is_alive():
            return

        logger.info("Stopping monitor...")
        self._stop_event.set()
        self._thread.join(timeout=timeout)

        if self._thread.is_alive():
            logger.warning("Monitor thread did not stop within timeout")
        else:
            logger.info("Monitor stopped")

    def is_running(self) -> bool:
        """Check if the monitor loop is currently running."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def internet_status(self) -> bool | None:
        """Get the current internet connectivity status.

        Returns:
            None if not yet checked, True if internet is available,
            False if no internet connectivity detected.
        """
        return self._internet_status

    def _run_loop(self) -> None:
        """Main monitor loop - runs in background thread."""
        logger.debug("Monitor loop started")

        while not self._stop_event.is_set():
            now = time.monotonic()
            targets_due = self._get_targets_due(now)

            if targets_due:
                self._check_targets(targets_due)
                self._cycle_count += 1

                # Run cleanup periodically
                if self._cycle_count >= CLEANUP_INTERVAL_CYCLES:
                    self._run_cleanup()
                    self._cycle_count = 0

            # Sleep briefly before checking again
            # Use wait() so we can be interrupted by stop_event
            self._stop_event.wait(timeout=1.0)

        logger.debug("Monitor loop exited")

    def _get_targets_due(self, now: float) -> list[TargetConfig]:
        """Get targets (URLs and TCP) that are due for a check."""
        due: list[TargetConfig] = []
        for target in self._config.all_targets:
            if now >= self._next_check.get(target.name, 0):
                due.append(target)
        return due

    def _get_urls_due(self, now: float) -> list[UrlConfig]:
        """Get URLs that are due for a check (for backward compatibility)."""
        due = []
        for url_config in self._config.urls:
            if now >= self._next_check.get(url_config.name, 0):
                due.append(url_config)
        return due

    def _check_targets(self, targets: list[TargetConfig]) -> None:
        """Check multiple targets concurrently and store results.

        When all targets fail, performs an internet connectivity check.
        If no internet, logs a single "NO INTERNET" warning instead of
        individual failure alerts.
        """
        results: list[CheckResult] = []
        target_configs: list[TargetConfig] = []

        # Collect all results first
        ssl_warning_days = self._config.monitor.ssl_warning_days
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(check_target, target, allow_private=False, ssl_warning_days=ssl_warning_days): target
                for target in targets
            }

            for future in as_completed(futures):
                target_config = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    target_configs.append(target_config)
                except Exception as e:
                    logger.error("Failed to check %s: %s", target_config.name, e)
                finally:
                    # Schedule next check for this target using global interval
                    self._next_check[target_config.name] = time.monotonic() + self._config.monitor.interval

        if not results:
            return

        # Check if all targets failed
        all_failed = all(not r.is_up for r in results)
        no_internet = False

        if all_failed and len(results) > 0:
            # All targets failed - check internet connectivity
            no_internet = not check_internet_connectivity()
            self._internet_status = not no_internet

            if no_internet:
                logger.warning("NO INTERNET - All targets unavailable")
        else:
            # At least one target is up, internet is available
            self._internet_status = True
            # Invalidate connectivity cache since we have confirmation internet works
            _connectivity_cache.invalidate()

        # Store results and log status
        for result in results:
            self._store_result(result)

            # Skip individual failure logging when no internet detected
            if no_internet and not result.is_up:
                continue

            status = "UP" if result.is_up else "DOWN"
            logger.debug(
                "%s: %s (%dms)",
                result.url_name,
                status,
                result.response_time_ms,
            )

    def _check_urls(self, urls: list[UrlConfig]) -> None:
        """Check multiple URLs concurrently and store results (backward compat)."""
        targets: list[TargetConfig] = list(urls)
        self._check_targets(targets)

    def _store_result(self, result: CheckResult) -> None:
        """Store a check result in the database and invoke callback."""
        try:
            insert_check(self._db_conn, result)
        except Exception as e:
            logger.error("Failed to store check result: %s", e)

        if self._on_check is not None:
            try:
                self._on_check(result)
            except Exception as e:
                logger.error("Check callback failed: %s", e)

    def _run_cleanup(self) -> None:
        """Run periodic cleanup of old check records."""
        retention_days = self._config.database.retention_days
        try:
            deleted = cleanup_old_checks(self._db_conn, retention_days)
            if deleted > 0:
                logger.info("Cleaned up %d old check records", deleted)
        except Exception as e:
            logger.error("Cleanup failed: %s", e)
