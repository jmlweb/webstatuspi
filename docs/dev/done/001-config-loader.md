# Task #001: Config Loader with Dataclasses

## Metadata
- **Status**: completed
- **Priority**: P2 - Next
- **Slice**: Config
- **Created**: 2026-01-16
- **Started**: 2026-01-16
- **Completed**: 2026-01-16
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a developer, I want to load and validate configuration from a YAML file using type-safe dataclasses.

**Acceptance Criteria**:
- [x] Define `Config` dataclass with all required fields
- [x] Define `UrlConfig` dataclass for URL entries
- [x] Load config from `config.yaml` file path
- [x] Validate required fields are present
- [x] Provide sensible defaults for optional fields
- [x] Handle file not found and parse errors gracefully
- [x] Support environment variable overrides (optional)

## Implementation Notes

### Config Structure Expected
```yaml
urls:
  - name: "Service A"
    url: "https://example.com/health"
    interval: 30  # seconds, optional (default: 60)
    timeout: 5    # seconds, optional (default: 10)

database:
  path: "./data/status.db"  # optional
  retention_days: 7  # days, optional (default: 7) - delete checks older than this

display:
  enabled: true  # optional
  cycle_interval: 5  # seconds between URL display

api:
  port: 8080  # optional
  enabled: true  # optional
```

### Dataclass Design
- Use `@dataclass` with `frozen=True` for immutability
- Use `Optional[]` types with defaults
- Consider `dacite` library for YAML→dataclass conversion (or manual)

### Pi 1B+ Constraints
- Keep imports minimal (no heavy validation libraries)
- Avoid runtime reflection if possible

## Files to Modify
- `src/config.py` (create) - Config dataclasses and loader
- `config.yaml` (create) - Example configuration file

## Dependencies
- None (this is the foundation task)

## Progress Log

### 2026-01-16
- Created `src/config.py` with dataclasses: `UrlConfig`, `DatabaseConfig`, `DisplayConfig`, `ApiConfig`, `Config`
- Used `frozen=True` for immutability on all dataclasses
- Implemented `load_config()` function with YAML parsing
- Added validation in `__post_init__` methods:
  - URL name max 10 chars (OLED constraint)
  - URL must be http/https
  - Intervals/timeouts must be positive
  - Port must be valid range
  - Duplicate URL names detected
- Implemented environment variable overrides for API and database settings
- Created `config.yaml` example with GOOGLE and GITHUB URLs
- Created `src/__init__.py` for package initialization
- Tested successfully: config loading and all error cases pass
- Task completed - all acceptance criteria met

## Learnings

Learnings transferred to LEARNINGS.md:
- L001: Manual YAML parsing is sufficient for config loading
- L002: Dataclass __post_init__ enables immutable validation
