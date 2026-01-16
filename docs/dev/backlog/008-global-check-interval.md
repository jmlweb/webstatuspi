# Task #008: Global Check Interval

## Metadata
- **Status**: in_progress
- **Priority**: P1 - Active
- **Slice**: Config Simplification
- **Created**: 2026-01-17
- **Started**: 2026-01-17
- **Blocked by**: #003 (should be done after monitor loop is working)

## Vertical Slice Definition

**User Story**: As a user, I want a single interval setting for all URL checks to simplify configuration.

**Acceptance Criteria**:
- [x] Move `interval` from per-URL config to global `monitor` section
- [x] Update `config.yaml` structure
- [x] Update `config.py` dataclasses and parsing
- [x] Keep `timeout` per-URL (different services may have different response times)
- [x] Update monitor loop to use global interval
- [x] Update documentation

## Current vs Proposed Configuration

### Current (per-URL interval)
```yaml
urls:
  - name: "UB_WEB"
    url: "https://www.unobravo.com"
    interval: 60  # per URL
    timeout: 10

  - name: "UB_APP"
    url: "https://app.unobravo.com"
    interval: 60  # per URL
    timeout: 10
```

### Proposed (global interval)
```yaml
monitor:
  interval: 60  # global: seconds between check cycles

urls:
  - name: "UB_WEB"
    url: "https://www.unobravo.com"
    timeout: 10

  - name: "UB_APP"
    url: "https://app.unobravo.com"
    timeout: 10
```

## Implementation Notes

### Config Changes
```python
@dataclass(frozen=True)
class MonitorConfig:
    """Configuration for the monitor loop."""
    interval: int = 60  # seconds between check cycles

    def __post_init__(self) -> None:
        if self.interval < 1:
            raise ConfigError("Monitor interval must be at least 1 second")

@dataclass(frozen=True)
class UrlConfig:
    """Configuration for a single URL to monitor."""
    name: str
    url: str
    timeout: int = 10  # interval removed
```

### Benefits
- Simpler configuration
- All URLs checked in the same cycle
- Easier to reason about system behavior
- Less configuration surface for errors

## Files to Modify
- `webstatuspi/config.py` - Add MonitorConfig, remove interval from UrlConfig
- `config.yaml` - Restructure with global interval
- `webstatuspi/monitor.py` - Use global interval from config
- `README.md` - Update configuration documentation

## Dependencies
- #003 Monitor loop (this refactors after monitor is working)

## Progress Log
- [2026-01-17 00:00] Started task
- [2026-01-17 00:01] Added MonitorConfig dataclass to config.py
- [2026-01-17 00:01] Removed interval from UrlConfig
- [2026-01-17 00:01] Added monitor field to Config with parsing and env override
- [2026-01-17 00:01] Updated config.yaml with global interval structure
- [2026-01-17 00:01] Updated monitor.py to use global interval
- [2026-01-17 00:01] Updated README.md documentation
- [2026-01-17 00:01] Updated tests to use new config structure
- [2026-01-17 00:01] All 46 tests passing

## Learnings
(None yet)
