# Task #001: Config Loader with Dataclasses

## Metadata
- **Status**: pending
- **Priority**: P2 - Next
- **Slice**: Config
- **Created**: 2026-01-16
- **Started**: -
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a developer, I want to load and validate configuration from a YAML file using type-safe dataclasses.

**Acceptance Criteria**:
- [ ] Define `Config` dataclass with all required fields
- [ ] Define `UrlConfig` dataclass for URL entries
- [ ] Load config from `config.yaml` file path
- [ ] Validate required fields are present
- [ ] Provide sensible defaults for optional fields
- [ ] Handle file not found and parse errors gracefully
- [ ] Support environment variable overrides (optional)

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
(No progress yet)

## Learnings
(None yet)
