# WebStatusPi - Project Rules

## Project Overview

WebStatusPi is a lightweight web monitoring system designed for Raspberry Pi 1B+. It monitors configured URLs, tracks success/failure statistics, and provides a JSON API.

**Hardware Target**: Raspberry Pi 1B+ (512MB RAM, single-core 700MHz ARM11)

## Tech Stack

- **Python**: 3.11+ (required for modern type hints and datetime.UTC constant)
- **HTTP Client**: `requests` library for URL monitoring
- **Database**: `sqlite3` (stdlib) for persistent storage
- **Web Server**: `http.server` (stdlib) for JSON API - zero dependencies
- **Configuration**: `PyYAML` for YAML parsing
- **Concurrency**: `threading` (stdlib) for concurrent monitoring + web server

## Code Style

Follow standard Python conventions and these project-specific rules.

### Python Guidelines

- **Type hints**: All functions must have type hints (Python 3.10+ union syntax `|` supported)
- **Dataclasses**: Use `dataclasses` for configuration and data transfer objects
- **No classes for logic**: Use modules with pure functions (classes only for data structures)
- **Functional approach**: Prefer immutability, avoid side effects where possible
- **Exception handling**: Only at boundaries (network I/O, file I/O, database operations)

### Module Organization

```python
# Standard library imports
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict

# Third-party imports
import requests
import yaml

# Local imports (if any)
from config import load_config
```

## Naming Conventions

- **Functions**: `snake_case` with descriptive names (`check_url`, `get_all_stats`)
- **Variables**: `snake_case` with auxiliary verbs where appropriate (`is_success`, `has_error`)
- **Constants**: `UPPER_SNAKE_CASE` (`DEFAULT_TIMEOUT`, `MAX_RETRIES`)
- **Types**: `PascalCase` for dataclasses and type aliases (`UrlConfig`, `CheckResult`)

### URL Name Convention

- Names must be **unique** across all URLs
- Names must be **≤ 10 characters** (optimized for OLED display)
- Use **uppercase and underscores** for readability (e.g., `APP_ES`, `API_PROD`)

## Dashboard Code Style

The HTML dashboard is embedded in `api.py` as `HTML_DASHBOARD`. Follow these guidelines when modifying it.

### CSS Guidelines

- **Use CSS custom properties**: All colors defined in `:root` (e.g., `--cyan`, `--red`, `--bg-dark`)
- **No external stylesheets**: All CSS must be inline in `<style>` tag
- **Font stack**: `'JetBrains Mono', 'Fira Code', 'Consolas', monospace`
- **Color palette** (cyberpunk theme):
  - `--cyan: #00fff9` - Primary accent, headers, success indicators
  - `--magenta: #ff00ff` - Secondary accent (reserved)
  - `--green: #00ff66` - Online/success status
  - `--red: #ff0040` - Offline/error status
  - `--yellow: #f0ff00` - Warning states
  - `--orange: #ff8800` - Degraded states

### CSS Naming

- **BEM-like classes**: `.card`, `.card-header`, `.card-name`
- **State modifiers**: `.card.down`, `.status-indicator.up`
- **Utility classes**: `.count-dimmed`, `.progress-fill.warning`

### Animation Guidelines

- **Performance**: Use `transform` and `opacity` for animations (GPU-accelerated)
- **Subtlety**: Keep CRT effects subtle (`opacity: 0.04` for scanlines)
- **Duration**: Long pauses between effect cycles (32s for scanline, 36s for flicker)
- **Purpose**: Animations should enhance UX, not distract
  - `pulse` - Live indicator heartbeat
  - `errorFlicker` - Attention on failures
  - `latencyPulse` - Data update feedback
  - `glitch` - Hover microinteraction

### JavaScript Guidelines

- **Vanilla JS only**: No frameworks or libraries
- **Polling interval**: 10 seconds (`POLL_INTERVAL = 10000`)
- **Data source**: Fetch from `/status` endpoint only
- **Error handling**: Display connection errors in `updatedTime` element
- **XSS prevention**: Always use `escapeHtml()` for user-generated content

### JavaScript Naming

- `UPPER_SNAKE_CASE` for constants (`POLL_INTERVAL`)
- `camelCase` for functions and variables (`formatTime`, `isUpdating`)
- Descriptive function names: `renderCard`, `getLatencyClass`, `fetchStatus`

### Adding New Features

1. **Colors**: Add to `:root` custom properties, never hardcode
2. **Cards**: Follow existing `.card` structure (header → metrics → footer)
3. **Metrics**: Use `.metric` grid layout with `.progress-bar` for visual indicators
4. **States**: Add modifier classes (`.card.warning`) rather than inline styles

### Do NOT

- Add external dependencies (CDN scripts, external CSS)
- Use `document.write()` or `innerHTML` with unescaped user input
- Create CPU-intensive animations (respect Pi 1B+ constraints)
- Add images or assets (keep dashboard self-contained)
- Use modern JS features not supported in older browsers (target ES6)

## Dependencies

### Minimal Dependencies (Pi 1B+ constraint)

```
PyYAML==6.0.1
requests==2.31.0
```

**Rationale**:
- No heavy frameworks (Flask, FastAPI add 50+ MB)
- Use stdlib wherever possible (`http.server`, `sqlite3`, `threading`, `json`)
- Only two external dependencies absolutely required

### Future Dependencies

When adding hardware features, see [docs/HARDWARE.md](docs/HARDWARE.md#future-dependencies-do-not-install-yet).

## Error Handling

### Network Errors

- **Timeouts**: Treat as failure, log as "Connection timeout"
- **DNS failures**: Treat as failure, log as "DNS resolution failed"
- **Connection refused**: Treat as failure, log as "Connection refused"
- **SSL errors**: Treat as failure, log specific SSL error

### Application Errors

- **Configuration errors**: Fail fast on startup (don't run with invalid config)
- **Database errors**: Log error, attempt to continue (monitoring more important than stats)
- **API errors**: Log error, return 500 status, keep monitoring running

### Graceful Degradation

- If database fails, continue monitoring but log to console only
- If API server fails to start, continue monitoring (primary function)
- If config reload fails, keep using previous valid configuration

## Logging Strategy

Keep logging minimal (SD card wear):

- **Console output**: All check results (success/failure)
- **Error logging**: Only for exceptions and failures
- **Info logging**: Startup, shutdown, configuration changes
- **Debug logging**: Available via `--verbose` flag, not enabled by default

**Do NOT log**:
- Successful routine operations
- Every database write
- API requests (unless error)

## Performance Constraints

The Raspberry Pi 1B+ has severe resource limitations:

- **CPU**: Single-core 700MHz ARM11 processor
- **RAM**: 512MB (shared with GPU ~256MB available)
- **Network**: 10/100 Ethernet only
- **Storage**: SD card (slow I/O, wear considerations)

**Design Constraints**:
- Must be extremely lightweight
- Avoid heavy frameworks (no Flask, FastAPI, Django)
- Use stdlib wherever possible
- Minimize dependencies
- Avoid CPU-intensive operations
- Minimize disk writes (SD card wear)

**Expected Targets**:
- CPU usage: < 20% with 5 URLs being monitored
- RAM usage: < 200MB steady state
- API response time: < 100ms
- Startup time: < 5 seconds

## Testing

### Testing Dependencies (Development Only)

```
pytest>=7.0.0
pytest-mock>=3.10.0
coverage>=7.0.0
```

### Manual Testing Checklist

- [ ] Start with valid config - system starts successfully
- [ ] Start with invalid config - system fails with clear error message
- [ ] Monitor URL that always succeeds (e.g., Google)
- [ ] Monitor URL that always fails (e.g., httpstat.us/500)
- [ ] Monitor URL that times out (e.g., httpstat.us/200?sleep=15000)
- [ ] API returns correct stats for all URLs
- [ ] API returns correct stats for specific URL
- [ ] API returns 404 for non-existent URL
- [ ] Run for 24 hours, check memory doesn't grow unbounded
- [ ] Disconnect network, verify graceful error handling
- [ ] Stop with Ctrl+C, verify graceful shutdown

## Console Output Format

Real-time monitoring output:

```
[2026-01-16 22:30:15] Google (https://www.google.com) - ✓ 200 OK (234ms)
[2026-01-16 22:30:45] Google (https://www.google.com) - ✗ 503 Service Unavailable (123ms)
```

**Format**: `[timestamp] name (url) - status status_code status_text (response_time)`
- Success: `✓` (green in terminals that support color)
- Failure: `✗` (red in terminals that support color)

## Required Reading

**Before starting any task**, consult **[docs/dev/LEARNINGS.md](docs/dev/LEARNINGS.md)** - this file contains critical lessons learned during development, including Pi 1B+ specific constraints, project patterns, and solutions to common problems. Ignoring this file may lead to repeating past mistakes.

## Documentation References

- **[README.md](README.md)** - User guide, API reference, configuration
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Guidelines for human contributors
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture, design decisions, database schema
- **[docs/HARDWARE.md](docs/HARDWARE.md)** - Hardware specifications, GPIO pin assignments
- **[docs/RESOURCES.md](docs/RESOURCES.md)** - Learning resources for hardware concepts (GPIO, I2C, etc.)
- **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[docs/testing/](docs/testing/)** - Testing strategies and mocking guidelines
- **[docs/dev/](docs/dev/)** - Task management and development workflow
- **[docs/dev/LEARNINGS.md](docs/dev/LEARNINGS.md)** - **CRITICAL**: Lessons learned, patterns, and past solutions

---

## Architecture Decision Log

Record of key architectural decisions made during development. Add new entries as decisions are made.

### ADR-001: stdlib-first HTTP Server

**Date**: 2026-01-16
**Status**: Accepted
**Context**: Need lightweight HTTP server for JSON API on Pi 1B+
**Decision**: Use `http.server` from stdlib instead of Flask/FastAPI
**Rationale**:
- Zero additional dependencies
- ~50MB RAM savings vs Flask
- Sufficient for simple JSON API
- Threading support via `ThreadingMixIn`
**Consequences**:
- Manual routing required
- No automatic JSON parsing
- Limited middleware support

### ADR-002: SQLite for Persistence

**Date**: 2026-01-16
**Status**: Accepted
**Context**: Need persistent storage for monitoring stats
**Decision**: Use SQLite via `sqlite3` stdlib module
**Rationale**:
- No external process (PostgreSQL/MySQL would use 100MB+ RAM)
- File-based, easy backup
- Sufficient for single-writer scenario
- stdlib, no dependencies
**Consequences**:
- Single-writer limitation (fine for this use case)
- No network access to DB
- Must handle WAL mode for SD card wear

### ADR-003: YAML for Configuration

**Date**: 2026-01-16
**Status**: Accepted
**Context**: Need human-readable configuration format
**Decision**: Use YAML via `PyYAML` library
**Rationale**:
- More readable than JSON for config files
- Supports comments
- Single small dependency acceptable
**Consequences**:
- One external dependency
- Must validate schema manually

### ADR-004: Embedded HTML Dashboard (Updated)

**Date**: 2026-01-18 (Updated: 2026-01-18)
**Status**: Accepted
**Context**: Need a visual dashboard for monitoring status without external dependencies
**Decision**: Embed HTML/CSS/JS as a Python string constant in `_dashboard.py`, imported by `api.py`
**Rationale**:
- Zero external files or static asset management
- No template engine dependency (Jinja2 would add ~5MB)
- Dashboard auto-refreshes via JavaScript fetch to `/status`
- CRT/cyberpunk aesthetic provides clear visual hierarchy
- Separate module improves maintainability without adding dependencies
**Consequences**:
- HTML changes isolated in dedicated `_dashboard.py` module
- Cleaner git diffs (HTML changes separate from Python logic)
- No hot-reload for frontend development
- Must follow embedded dashboard guidelines (see Dashboard Code Style section)
**Update (2026-01-18)**: Evaluated template engines (Jinja2, string.Template, str.format).
Finding: Dashboard uses client-side rendering, no server-side templating needed.
Separated HTML to `_dashboard.py` for better maintainability while keeping zero dependencies.

<!-- Add new ADRs above this line -->

### Template for New ADRs

```markdown
### ADR-XXX: Title

**Date**: YYYY-MM-DD
**Status**: Proposed | Accepted | Deprecated | Superseded
**Context**: What is the issue that we're seeing that is motivating this decision?
**Decision**: What is the change that we're proposing and/or doing?
**Rationale**: Why this decision over alternatives?
**Consequences**: What becomes easier or more difficult because of this decision?
```
