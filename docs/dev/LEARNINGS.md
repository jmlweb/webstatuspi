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

(No learnings yet)

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
