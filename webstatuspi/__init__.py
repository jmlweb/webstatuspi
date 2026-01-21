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


def _cmd_run(args: argparse.Namespace) -> None:
    """Execute the run command - start the monitoring service."""
    global _shutdown_event

    _setup_logging(args.verbose)

    logger.info("WebStatusPi %s starting...", __version__)

    # Import here to avoid circular imports and allow logging setup first
    from .config import load_config, ConfigError
    from .database import init_db, DatabaseError
    from .monitor import Monitor
    from .api import ApiServer, ApiError
    from .alerter import Alerter

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

    # 4. Initialize alerter
    alerter = Alerter(config.alerts)
    if config.alerts.webhooks:
        logger.info("Alerts configured with %d webhook(s)", len(config.alerts.webhooks))

    # 5. Start components
    monitor = Monitor(config, db_conn, on_check=alerter.process_check_result)
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

        # 6. Wait for shutdown signal
        _shutdown_event.wait()

    except KeyboardInterrupt:
        # Backup handler if signal doesn't work
        logger.info("Keyboard interrupt received")
    finally:
        # 7. Cleanup - stop all components
        logger.info("Shutting down components...")

        monitor.stop()

        if api_server is not None:
            api_server.stop()

        db_conn.close()
        logger.info("Database connection closed")

        logger.info("Shutdown complete")


def _cmd_install_service(args: argparse.Namespace) -> None:
    """Execute the install-service command."""
    from .service import detect_paths, install_service

    # Get default paths
    defaults = detect_paths()

    # Use provided values or defaults
    user = args.user or defaults["user"]
    working_dir = args.working_dir or defaults["working_dir"]
    python_path = defaults["python_path"]

    success = install_service(
        user=user,
        working_dir=working_dir,
        python_path=python_path,
        enable=args.enable,
        start=args.start,
        dry_run=args.dry_run,
    )

    if not success:
        sys.exit(1)


def _cmd_clean(args: argparse.Namespace) -> None:
    """Execute the clean command - remove old check records from the database."""
    from pathlib import Path

    from .config import load_config, ConfigError
    from .database import cleanup_old_checks, delete_all_checks, DatabaseError

    # 1. Load configuration
    try:
        config = load_config(args.config)
    except ConfigError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # 2. Validate database exists
    db_path = Path(config.database.path)
    if not db_path.exists():
        print(f"Error: Database not found at {config.database.path}")
        sys.exit(1)

    # 3. Determine retention days
    if args.all:
        retention_days = None  # Delete all
    elif args.retention_days is not None:
        if args.retention_days < 0:
            print("Error: retention-days must be a non-negative integer")
            sys.exit(1)
        retention_days = args.retention_days
    else:
        retention_days = config.database.retention_days

    # 4. Connect to database and perform cleanup
    import sqlite3
    try:
        conn = sqlite3.connect(config.database.path)
        conn.row_factory = sqlite3.Row

        if retention_days is None:
            deleted = delete_all_checks(conn)
            print(f"Deleted all {deleted} check records from database.")
        else:
            deleted = cleanup_old_checks(conn, retention_days)
            print(f"Deleted {deleted} check records older than {retention_days} days.")

        conn.close()

    except sqlite3.Error as e:
        print(f"Error: Database error - {e}")
        sys.exit(1)
    except DatabaseError as e:
        print(f"Error: {e}")
        sys.exit(1)


def _cmd_test_alert(args: argparse.Namespace) -> None:
    """Execute the test-alert command - verify webhook configuration."""
    from .config import load_config, ConfigError
    from .alerter import Alerter

    # 1. Load configuration
    try:
        config = load_config(args.config)
    except ConfigError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # 2. Check if any webhooks are configured
    if not config.alerts.webhooks:
        print("Error: No webhooks configured in alerts section")
        sys.exit(1)

    # 3. Create alerter and test webhooks
    alerter = Alerter(config.alerts)
    print(f"Testing {len(config.alerts.webhooks)} webhook(s)...\n")

    results = alerter.test_webhooks()

    # 4. Display results
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)

    for url, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{status}: {url}")

    print(f"\nResult: {success_count}/{total_count} webhooks successful")

    if success_count < total_count:
        sys.exit(1)


def main() -> None:
    """Main entry point for the webstatuspi package."""
    parser = argparse.ArgumentParser(
        description="WebStatusPi - Lightweight web monitoring for Raspberry Pi"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"webstatuspi {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")

    # Run subcommand (default behavior)
    run_parser = subparsers.add_parser(
        "run",
        help="Start the monitoring service (default)",
    )
    run_parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    run_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging",
    )
    run_parser.set_defaults(func=_cmd_run)

    # Install-service subcommand
    install_parser = subparsers.add_parser(
        "install-service",
        help="Install systemd service for auto-start",
    )
    install_parser.add_argument(
        "--user",
        help="User to run the service as (default: current user)",
    )
    install_parser.add_argument(
        "--working-dir",
        help="Working directory for the service (default: current directory)",
    )
    install_parser.add_argument(
        "--enable",
        action="store_true",
        help="Enable service for auto-start on boot",
    )
    install_parser.add_argument(
        "--start",
        action="store_true",
        help="Start the service immediately after installation",
    )
    install_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the service file without installing",
    )
    install_parser.set_defaults(func=_cmd_install_service)

    # Clean subcommand
    clean_parser = subparsers.add_parser(
        "clean",
        help="Remove old check records from the database",
    )
    clean_parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    clean_parser.add_argument(
        "--retention-days",
        type=int,
        help="Delete records older than this many days (overrides config)",
    )
    clean_parser.add_argument(
        "--all",
        action="store_true",
        help="Delete all check records (ignores retention_days)",
    )
    clean_parser.set_defaults(func=_cmd_clean)

    # Test-alert subcommand
    test_alert_parser = subparsers.add_parser(
        "test-alert",
        help="Test webhook alert configuration",
    )
    test_alert_parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    test_alert_parser.set_defaults(func=_cmd_test_alert)

    args = parser.parse_args()

    # Default to 'run' if no command specified (backward compatibility)
    if args.command is None:
        # Re-parse with default values for run command
        args.config = "config.yaml"
        args.verbose = False
        args.func = _cmd_run

    args.func(args)
