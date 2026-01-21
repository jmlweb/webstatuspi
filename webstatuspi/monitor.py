"""URL monitoring loop with threaded health checks."""

import logging
import socket
import sqlite3
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from threading import Event, Thread

from .config import Config, UrlConfig
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


def check_url(url_config: UrlConfig, allow_private: bool = False) -> CheckResult:
    """Perform a single HTTP health check on a URL.

    Args:
        url_config: Configuration for the URL to check.
        allow_private: If True, allow private IPs (for testing only).

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

    try:
        request = urllib.request.Request(
            url_config.url,
            method="GET",
            headers={"User-Agent": "WebStatusPi/0.1"},
        )
        with _opener.open(request, timeout=url_config.timeout) as response:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            status_code = response.status
            is_up = 200 <= status_code < 400

            return CheckResult(
                url_name=url_config.name,
                url=url_config.url,
                status_code=status_code,
                response_time_ms=elapsed_ms,
                is_up=is_up,
                error_message=None,
                checked_at=checked_at,
            )

    except urllib.error.HTTPError as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        # Treat 3xx redirects as "up" - server is responding
        is_up = 300 <= e.code < 400
        return CheckResult(
            url_name=url_config.name,
            url=url_config.url,
            status_code=e.code,
            response_time_ms=elapsed_ms,
            is_up=is_up,
            error_message=None if is_up else f"HTTP {e.code}: {e.reason}",
            checked_at=checked_at,
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
            error_message=reason,
            checked_at=checked_at,
        )

    except Exception as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return CheckResult(
            url_name=url_config.name,
            url=url_config.url,
            status_code=None,
            response_time_ms=elapsed_ms,
            is_up=False,
            error_message=str(e),
            checked_at=checked_at,
        )


class Monitor:
    """Threaded URL monitor that checks URLs at a global interval.

    All URLs are checked together at the configured monitor interval.
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
            config: Application configuration with URLs to monitor.
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

        # Track next check time for each URL (staggered start)
        self._next_check: dict[str, float] = {}
        now = time.monotonic()
        for i, url_config in enumerate(config.urls):
            # Stagger initial checks by 2 seconds each to avoid burst
            self._next_check[url_config.name] = now + (i * 2)

    def start(self) -> None:
        """Start the monitor loop in a background thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Monitor already running")
            return

        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, daemon=True, name="monitor-loop")
        self._thread.start()
        logger.info("Monitor started with %d URLs", len(self._config.urls))

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
            urls_due = self._get_urls_due(now)

            if urls_due:
                self._check_urls(urls_due)
                self._cycle_count += 1

                # Run cleanup periodically
                if self._cycle_count >= CLEANUP_INTERVAL_CYCLES:
                    self._run_cleanup()
                    self._cycle_count = 0

            # Sleep briefly before checking again
            # Use wait() so we can be interrupted by stop_event
            self._stop_event.wait(timeout=1.0)

        logger.debug("Monitor loop exited")

    def _get_urls_due(self, now: float) -> list[UrlConfig]:
        """Get URLs that are due for a check."""
        due = []
        for url_config in self._config.urls:
            if now >= self._next_check.get(url_config.name, 0):
                due.append(url_config)
        return due

    def _check_urls(self, urls: list[UrlConfig]) -> None:
        """Check multiple URLs concurrently and store results.

        When all URLs fail, performs an internet connectivity check.
        If no internet, logs a single "NO INTERNET" warning instead of
        individual failure alerts.
        """
        results: list[CheckResult] = []
        url_configs: list[UrlConfig] = []

        # Collect all results first
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(check_url, url): url for url in urls}

            for future in as_completed(futures):
                url_config = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    url_configs.append(url_config)
                except Exception as e:
                    logger.error("Failed to check %s: %s", url_config.name, e)
                finally:
                    # Schedule next check for this URL using global interval
                    self._next_check[url_config.name] = time.monotonic() + self._config.monitor.interval

        if not results:
            return

        # Check if all URLs failed
        all_failed = all(not r.is_up for r in results)
        no_internet = False

        if all_failed and len(results) > 0:
            # All URLs failed - check internet connectivity
            no_internet = not check_internet_connectivity()
            self._internet_status = not no_internet

            if no_internet:
                logger.warning("NO INTERNET - All URLs unavailable")
        else:
            # At least one URL is up, internet is available
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
