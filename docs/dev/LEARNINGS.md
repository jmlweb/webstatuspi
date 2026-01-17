# Development Learnings

This file captures lessons learned during development. Each learning has a unique ID for reference.

## Index by Category
- [Hardware](#hardware)
- [Performance](#performance)
- [Configuration](#configuration)
- [Database](#database)
- [API](#api)

---

## Hardware

### L006: Always verify target OS configuration before hardware decisions
**Date**: 2026-01-17
**Task**: Hardware architecture review
**Context**: Initial analysis assumed ~256MB available RAM (desktop mode). This led to premature decision to remove OLED display to support 8-10 URLs.
**Learning**: Hardware resource analysis must account for the actual OS configuration. The Pi 1B+ (512MB) has vastly different available RAM depending on configuration: Desktop (~256-384MB) vs Lite + `gpu_mem=16` (~496MB). A 2x difference in available RAM completely changes what's feasible. Always ask about OS configuration before making hardware decisions.
**Action**: Updated all documentation to reflect Raspberry Pi OS Lite as target. OLED display retained since RAM is not a constraint.

### L007: Raspberry Pi OS Lite provides ~2x more RAM than desktop
**Date**: 2026-01-17
**Task**: Hardware architecture review
**Context**: Initial hardware load analysis assumed ~256MB available RAM based on typical Pi 1B+ documentation.
**Learning**: The Pi 1B+ has 512MB total RAM shared with GPU. With desktop, GPU takes 128-256MB leaving ~256-384MB. With **Lite + `gpu_mem=16`**, only 16MB goes to GPU leaving **~496MB available** - nearly double. With ~496MB available and ~136-234MB estimated usage (with display), utilization is only ~27-47%. This provides comfortable headroom for 10 URLs with OLED display.
**Action**: Updated HARDWARE-LOAD-ANALYSIS.md with Lite-specific numbers. OLED display retained in design.

---

## Performance

### L008: time.monotonic() prevents clock-based measurement errors
**Date**: 2026-01-17
**Task**: #003 Monitor loop with threading
**Context**: Implementing accurate response time measurement for URL health checks
**Learning**: `time.monotonic()` is unaffected by system clock changes (NTP adjustments, DST, manual changes) unlike `time.time()`. This ensures response time measurements are always accurate even if the system clock jumps backward or forward during a check.
**Action**: Used `time.monotonic()` for all elapsed time measurements in `check_url()` function

### L009: threading.Event.wait() enables graceful shutdown
**Date**: 2026-01-17
**Task**: #003 Monitor loop with threading
**Context**: Implementing graceful shutdown for the monitor loop
**Learning**: `threading.Event.wait(timeout)` is immediately interruptible when the event is set, unlike `time.sleep()` which blocks until the full duration completes. This allows the monitor loop to respond instantly to shutdown signals while still sleeping between checks.
**Action**: Used `self._stop_event.wait(timeout=1.0)` in the monitor loop instead of `time.sleep(1.0)`

### L010: Staggered startup prevents resource burst
**Date**: 2026-01-17
**Task**: #003 Monitor loop with threading
**Context**: Optimizing monitor startup for Pi 1B+ with multiple URLs
**Learning**: Starting all URL checks simultaneously causes CPU and network bursts. Staggering initial checks by 2 seconds per URL spreads the load evenly and prevents resource spikes, especially important on resource-constrained hardware like Pi 1B+.
**Action**: Initialize `_next_check` times with staggered delays: `now + (i * 2)` for each URL

---

## Configuration

### L001: Manual YAML parsing is sufficient for config loading
**Date**: 2026-01-16
**Task**: #001 Config loader with dataclasses
**Context**: Needed to convert YAML config to dataclasses while minimizing dependencies for Pi 1B+
**Learning**: Manual YAML→dataclass conversion is straightforward and avoids adding dependencies like `dacite`. Simple factory functions work well for parsing each config section.
**Action**: Implemented manual parsing functions (`_parse_url_config`, `_parse_database_config`, etc.) in `src/config.py`

### L002: Dataclass __post_init__ enables immutable validation
**Date**: 2026-01-16
**Task**: #001 Config loader with dataclasses
**Context**: Needed to validate config values while keeping dataclasses immutable
**Learning**: Python's `__post_init__` method works perfectly with `frozen=True` dataclasses. Validation runs after initialization but before the object is frozen, allowing us to enforce constraints while maintaining immutability.
**Action**: Added validation logic in `__post_init__` methods for all config dataclasses

---

## Database

### L003: Project structure uses webstatuspi/ not src/
**Date**: 2026-01-17
**Task**: #002 Database Layer (SQLite)
**Context**: Creating database and model files for the project
**Learning**: The project follows the package name structure with `webstatuspi/` as the source directory, not the common `src/` pattern. This is set up via setuptools.packages.find in pyproject.toml.
**Action**: Created files in `webstatuspi/database.py` and `webstatuspi/models.py`

### L004: WAL mode improves SQLite concurrent read performance on Pi
**Date**: 2026-01-17
**Task**: #002 Database Layer (SQLite)
**Context**: Optimizing database for Pi 1B+ with limited resources and concurrent API reads
**Learning**: SQLite's WAL (Write-Ahead Logging) mode allows multiple readers to access the database simultaneously without blocking, even during writes. This is crucial for serving API requests while monitoring continues.
**Action**: Enabled WAL mode via `PRAGMA journal_mode=WAL` in `init_db()` function

### L005: Composite indexes optimize time-range queries
**Date**: 2026-01-17
**Task**: #002 Database Layer (SQLite)
**Context**: Implementing efficient history queries filtered by both URL name and time range
**Learning**: Adding a composite index on `(url_name, checked_at)` significantly improves performance for queries that filter by URL and time range, which is the most common query pattern for this application.
**Action**: Created `idx_checks_url_name_checked_at` composite index in addition to individual indexes

---

## API

### L011: Factory pattern to inject dependencies into BaseHTTPRequestHandler
**Date**: 2026-01-17
**Task**: #004 API server for JSON stats
**Context**: Needed to pass database connection to the HTTP request handler, but `BaseHTTPRequestHandler.__init__` doesn't accept custom arguments.
**Learning**: Create a factory function that returns a subclass with dependencies bound as class attributes. This pattern (`_create_handler_class(db_conn)`) creates a new class with `db_conn` set, allowing each request to access shared resources without modifying the handler's constructor signature.
**Action**: Implemented `_create_handler_class()` that returns `BoundStatusHandler` with `db_conn` as class attribute

### L012: Use handle_request() instead of serve_forever() for graceful shutdown
**Date**: 2026-01-17
**Task**: #004 API server for JSON stats
**Context**: Implementing graceful shutdown for the API server thread
**Learning**: `HTTPServer.serve_forever()` blocks indefinitely and is difficult to interrupt cleanly. Using `handle_request()` in a loop with `server.timeout = 1.0` allows periodic checking of a shutdown event. This enables the server to respond to shutdown signals within 1 second while still handling requests normally.
**Action**: Implemented `_serve_forever()` loop with `handle_request()` and `_shutdown_event` check

### L013: Override log_message() to integrate with Python logging
**Date**: 2026-01-17
**Task**: #004 API server for JSON stats
**Context**: BaseHTTPRequestHandler writes access logs directly to stderr, bypassing application logging
**Learning**: Override `log_message(self, format, *args)` to redirect HTTP access logs to Python's logging module. This integrates all application logs in a consistent format and respects log levels (e.g., only show in debug mode).
**Action**: Overrode `log_message()` to use `logger.debug()` instead of stderr

### L014: Connection: close header simplifies single-threaded HTTP servers
**Date**: 2026-01-17
**Task**: #004 API server for JSON stats
**Context**: Implementing lightweight HTTP server on resource-constrained Pi 1B+
**Learning**: Adding `Connection: close` header tells clients not to reuse the connection. This avoids HTTP keep-alive complexity in single-threaded servers, prevents connection accumulation, and simplifies resource management. The minor overhead of new connections is negligible for low-traffic monitoring APIs.
**Action**: Added `Connection: close` header in `_send_json()` method

### L015: Client-side rendering eliminates need for server-side templating
**Date**: 2026-01-18
**Task**: #011 Evaluate dashboard templates vs embedded HTML
**Context**: Evaluating whether to use template engines (Jinja2, string.Template) for the dashboard instead of embedded HTML
**Learning**: The dashboard uses client-side JavaScript rendering (fetch from `/status`, render with DOM manipulation). All dynamic content is rendered in the browser, not on the server. Template engines like Jinja2 are designed for server-side rendering and provide no functional benefit when the server only sends static HTML that fetches data via AJAX. This is a common pattern in modern web apps and eliminates the need for server-side templating dependencies.
**Action**: Documented in ADR-004. Kept embedded HTML approach, avoiding Jinja2 dependency (~144KB + MarkupSafe)

### L016: Module separation improves maintainability without adding dependencies
**Date**: 2026-01-18
**Task**: #011 Evaluate dashboard templates vs embedded HTML
**Context**: Addressing maintainability concerns with 35KB HTML embedded in api.py (78% of file)
**Learning**: Extracting embedded content to a separate Python module (`_dashboard.py`) provides the maintainability benefits of file separation while preserving all runtime advantages of embedded strings: zero dependencies, zero I/O overhead, single import at module load. This gives cleaner git diffs (HTML changes isolated from Python logic) and better code organization without any performance or deployment cost. The underscore prefix signals it's an internal implementation detail.
**Action**: Created `webstatuspi/_dashboard.py` with `HTML_DASHBOARD` constant. Reduced `api.py` from 44KB to 10KB (Python only). All 27 tests pass.

---

## Learning Template

When adding a new learning, use this format:

```markdown
### LXXX: Brief title describing the learning
**Date**: YYYY-MM-DD
**Task**: #XXX Task name
**Context**: What were you trying to do?
**Learning**: What did you discover?
**Action**: How was this documented/applied?
```
