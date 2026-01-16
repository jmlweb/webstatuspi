# Task #005: Main Orchestration & Graceful Shutdown

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: Core
- **Created**: 2026-01-16
- **Started**: -
- **Blocked by**: #003, #004 (dependencies #001, #002 completed)

## Vertical Slice Definition

**User Story**: As an operator, I want the application to start all components and shutdown gracefully on SIGTERM/SIGINT.

**Acceptance Criteria**:
- [ ] Single entry point (`main.py` or `__main__.py`)
- [ ] Load configuration first
- [ ] Initialize database
- [ ] Start monitor loop in background
- [ ] Start API server in background
- [ ] Handle SIGTERM and SIGINT for graceful shutdown
- [ ] Stop all threads cleanly before exit
- [ ] Log startup and shutdown events

## Implementation Notes

### Main Structure
```python
import signal
import sys
from config import load_config
from database import init_db
from monitor import MonitorLoop
from api import start_api_server

def main():
    # 1. Load config
    config = load_config("config.yaml")

    # 2. Init database
    db_conn = init_db(config.database.path)

    # 3. Setup shutdown handler
    shutdown_event = threading.Event()

    def handle_shutdown(signum, frame):
        print("Shutdown signal received...")
        shutdown_event.set()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # 4. Start components
    monitor = MonitorLoop(config, db_conn, shutdown_event)
    monitor.start()

    if config.api.enabled:
        api_thread = start_api_server(config, db_conn)

    # 5. Wait for shutdown
    shutdown_event.wait()

    # 6. Cleanup
    monitor.stop()
    if config.api.enabled:
        api_thread.stop()

    db_conn.close()
    print("Shutdown complete")

if __name__ == "__main__":
    main()
```

### Logging Strategy
- Use `logging` module with configurable level
- Log to stdout (for systemd/docker capture)
- Include timestamps and component names

### Pi 1B+ Constraints
- Keep main loop simple (avoid polling for shutdown)
- Use `threading.Event` for clean signaling
- Consider startup delay between components

## Files to Modify
- `webstatuspi/main.py` (create) - Entry point and orchestration
- `webstatuspi/__init__.py` (update) - Already exists from #006

## Dependencies
- #001 Config loader
- #002 Database layer
- #003 Monitor loop
- #004 API server

## Progress Log
(No progress yet)

## Learnings
(None yet)
