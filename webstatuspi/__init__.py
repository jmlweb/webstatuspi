"""WebStatusPi - Lightweight web monitoring for Raspberry Pi."""

import argparse
import logging
import signal
import sys
from threading import Event
from typing import Optional

__version__ = "0.1.0"

# Global shutdown event for signal handlers
_shutdown_event: Optional[Event] = None

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def _handle_shutdown(signum: int, frame: object) -> None:
    """Signal handler for graceful shutdown."""
    sig_name = signal.Signals(signum).name
    logger.info("Received %s, initiating shutdown...", sig_name)
    if _shutdown_event is not None:
        _shutdown_event.set()


def main() -> None:
    """Main entry point for the webstatuspi package."""
    global _shutdown_event

    parser = argparse.ArgumentParser(
        description="WebStatusPi - Lightweight web monitoring for Raspberry Pi"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"webstatuspi {__version__}",
    )
    args = parser.parse_args()

    _setup_logging(args.verbose)

    logger.info("WebStatusPi %s starting...", __version__)

    # Import here to avoid circular imports and allow logging setup first
    from .config import load_config, ConfigError
    from .database import init_db, DatabaseError
    from .monitor import Monitor
    from .api import ApiServer, ApiError

    # 1. Load configuration
    try:
        config = load_config(args.config)
        logger.info("Configuration loaded from %s", args.config)
        logger.info("Monitoring %d URLs at %ds interval", len(config.urls), config.monitor.interval)
    except ConfigError as e:
        logger.error("Configuration error: %s", e)
        sys.exit(1)

    # 2. Initialize database
    try:
        db_conn = init_db(config.database.path)
        logger.info("Database initialized at %s", config.database.path)
    except DatabaseError as e:
        logger.error("Database error: %s", e)
        sys.exit(1)

    # 3. Setup shutdown handler
    _shutdown_event = Event()
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    # 4. Start components
    monitor = Monitor(config, db_conn)
    api_server: Optional[ApiServer] = None

    try:
        monitor.start()

        if config.api.enabled:
            try:
                api_server = ApiServer(config.api, db_conn)
                api_server.start()
            except ApiError as e:
                logger.error("Failed to start API server: %s", e)
                logger.warning("Continuing without API server")
                api_server = None

        logger.info("All components started, waiting for shutdown signal...")

        # 5. Wait for shutdown signal
        _shutdown_event.wait()

    except KeyboardInterrupt:
        # Backup handler if signal doesn't work
        logger.info("Keyboard interrupt received")
    finally:
        # 6. Cleanup - stop all components
        logger.info("Shutting down components...")

        monitor.stop()

        if api_server is not None:
            api_server.stop()

        db_conn.close()
        logger.info("Database connection closed")

        logger.info("Shutdown complete")
