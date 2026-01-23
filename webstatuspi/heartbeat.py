"""Heartbeat module for self-monitoring.

Sends periodic pings to external monitoring services like Healthchecks.io
or Dead Man's Snitch to ensure WebStatusPi itself is running.
"""

import logging
import threading
import urllib.request
from urllib.error import URLError

from webstatuspi.config import HeartbeatConfig

logger = logging.getLogger(__name__)


class Heartbeat:
    """Sends periodic heartbeat pings to external monitoring service."""

    def __init__(self, config: HeartbeatConfig) -> None:
        """Initialize heartbeat with configuration.

        Args:
            config: Heartbeat configuration including URL and interval.
        """
        self.config = config
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start heartbeat thread."""
        if not self.config.enabled:
            logger.info("Heartbeat disabled")
            return

        if self._thread and self._thread.is_alive():
            logger.warning("Heartbeat already running")
            return

        self._thread = threading.Thread(target=self._run, name="heartbeat", daemon=True)
        self._thread.start()
        logger.info("Heartbeat started (interval: %ds, URL: %s)", self.config.interval_seconds, self._mask_url())

    def stop(self) -> None:
        """Stop heartbeat thread gracefully."""
        if not self._thread or not self._thread.is_alive():
            return

        logger.info("Stopping heartbeat...")
        self._stop_event.set()
        self._thread.join(timeout=5)

        if self._thread.is_alive():
            logger.warning("Heartbeat thread did not stop gracefully")
        else:
            logger.info("Heartbeat stopped")

    def _run(self) -> None:
        """Main heartbeat loop - runs in background thread."""
        while not self._stop_event.is_set():
            self._send_ping()
            # Wait for interval or until stop signal
            self._stop_event.wait(self.config.interval_seconds)

    def _send_ping(self) -> None:
        """Send a single heartbeat ping to the configured URL."""
        try:
            req = urllib.request.Request(self.config.url, headers={"User-Agent": "WebStatusPi-Heartbeat/1.0"})
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                if resp.status < 400:
                    logger.debug("Heartbeat ping successful: %d", resp.status)
                else:
                    logger.warning("Heartbeat ping returned %d", resp.status)
        except URLError as e:
            logger.warning("Heartbeat ping failed: %s", e)
        except Exception as e:
            logger.error("Heartbeat unexpected error: %s", e)

    def _mask_url(self) -> str:
        """Mask sensitive tokens in URL for logging.

        Returns:
            URL with path masked if it contains sensitive tokens.
        """
        try:
            from urllib.parse import urlparse

            parsed = urlparse(self.config.url)
            if parsed.path and len(parsed.path) > 10:
                # Mask most of the path, keep first 3 chars
                masked_path = parsed.path[:3] + "***"
                return f"{parsed.scheme}://{parsed.netloc}{masked_path}"
            return self.config.url
        except Exception:
            return "***"
