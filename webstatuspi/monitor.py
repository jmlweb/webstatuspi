"""URL monitoring loop with threaded health checks."""

import logging
import sqlite3
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from threading import Event, Thread
from typing import Callable, Dict, List, Optional

from .config import Config, UrlConfig
from .database import cleanup_old_checks, insert_check
from .models import CheckResult

logger = logging.getLogger(__name__)

# Pi 1B+ optimized: limit concurrent checks
MAX_WORKERS = 3
# Run cleanup every N check cycles to minimize SD card writes
CLEANUP_INTERVAL_CYCLES = 100


def check_url(url_config: UrlConfig) -> CheckResult:
    """Perform a single HTTP health check on a URL.

    Args:
        url_config: Configuration for the URL to check.

    Returns:
        CheckResult with status, response time, and any error details.
    """
    start = time.monotonic()
    checked_at = datetime.utcnow()

    try:
        request = urllib.request.Request(
            url_config.url,
            method="GET",
            headers={"User-Agent": "WebStatusPi/0.1"},
        )
        with urllib.request.urlopen(request, timeout=url_config.timeout) as response:
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
        return CheckResult(
            url_name=url_config.name,
            url=url_config.url,
            status_code=e.code,
            response_time_ms=elapsed_ms,
            is_up=False,
            error_message=f"HTTP {e.code}: {e.reason}",
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
        on_check: Optional[Callable[[CheckResult], None]] = None,
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
        self._thread: Optional[Thread] = None
        self._cycle_count = 0

        # Track next check time for each URL (staggered start)
        self._next_check: Dict[str, float] = {}
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

    def _get_urls_due(self, now: float) -> List[UrlConfig]:
        """Get URLs that are due for a check."""
        due = []
        for url_config in self._config.urls:
            if now >= self._next_check.get(url_config.name, 0):
                due.append(url_config)
        return due

    def _check_urls(self, urls: List[UrlConfig]) -> None:
        """Check multiple URLs concurrently and store results."""
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(check_url, url): url for url in urls}

            for future in as_completed(futures):
                url_config = futures[future]
                try:
                    result = future.result()
                    self._store_result(result)

                    # Schedule next check for this URL using global interval
                    self._next_check[url_config.name] = (
                        time.monotonic() + self._config.monitor.interval
                    )

                    status = "UP" if result.is_up else "DOWN"
                    logger.debug(
                        "%s: %s (%dms)",
                        result.url_name,
                        status,
                        result.response_time_ms,
                    )

                except Exception as e:
                    logger.error("Failed to check %s: %s", url_config.name, e)
                    # Still schedule next check even on error
                    self._next_check[url_config.name] = (
                        time.monotonic() + self._config.monitor.interval
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
