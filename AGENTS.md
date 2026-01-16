# WebStatusPi - Project Rules

## Project Overview

WebStatusPi is a lightweight web monitoring system designed for Raspberry Pi 1B+. It monitors configured URLs, tracks success/failure statistics, and provides a JSON API.

**Hardware Target**: Raspberry Pi 1B+ (512MB RAM, single-core 700MHz ARM11)

## Tech Stack

- **Python**: 3.7+ (compatibility with older Raspberry Pi OS versions)
- **HTTP Client**: `requests` library for URL monitoring
- **Database**: `sqlite3` (stdlib) for persistent storage
- **Web Server**: `http.server` (stdlib) for JSON API - zero dependencies
- **Configuration**: `PyYAML` for YAML parsing
- **Concurrency**: `threading` (stdlib) for concurrent monitoring + web server

## Code Style

Follow standard Python conventions and these project-specific rules.

### Python Guidelines

- **Type hints**: All functions must have type hints (Python 3.7+ compatible)
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

## Documentation References

- **[README.md](README.md)** - User guide, API reference, configuration
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture, design decisions, database schema
- **[docs/HARDWARE.md](docs/HARDWARE.md)** - Hardware specifications, GPIO pin assignments
- **[docs/testing/](docs/testing/)** - Testing strategies and mocking guidelines
- **[docs/dev/](docs/dev/)** - Task management and development workflow

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
