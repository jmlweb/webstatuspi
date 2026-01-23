# Task #030: Configurable User-Agent

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: Core, Config
- **Created**: 2026-01-23
- **Started**: -
- **Completed**: -
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a system administrator, I want to configure the User-Agent header for HTTP requests so that I can avoid being blocked by WAFs (Cloudflare, Akamai, etc.) that reject requests from unknown or bot-like User-Agents.

**Acceptance Criteria**:
- [ ] Config schema supports global `default_user_agent` option
- [ ] Config schema supports per-URL `user_agent` override
- [ ] Monitor uses configured User-Agent in HTTP requests
- [ ] Default User-Agent remains `WebStatusPi/X.X` if not configured
- [ ] Unit tests for User-Agent configuration
- [ ] Documentation added to README.md with examples

## Implementation Notes

### Config Schema Addition

```yaml
monitor:
  default_user_agent: "Mozilla/5.0 (compatible; WebStatusPi/1.0; +https://github.com/user/webstatuspi)"

urls:
  - name: "api-with-waf"
    url: "https://api.example.com/health"
    user_agent: "CustomMonitor/1.0"  # Override for this URL only

  - name: "normal-api"
    url: "https://other.example.com"
    # Uses default_user_agent
```

### Implementation in monitor.py

Current code (line ~511):
```python
headers = {"User-Agent": "WebStatusPi/0.1"}
```

Change to:
```python
user_agent = url_config.user_agent or config.monitor.default_user_agent or "WebStatusPi/0.1"
headers = {"User-Agent": user_agent}
```

### Config Changes

Add to `MonitorConfig` dataclass:
```python
@dataclass
class MonitorConfig:
    check_interval: int = 60
    default_user_agent: str = "WebStatusPi/0.1"
```

Add to `UrlConfig` dataclass:
```python
@dataclass
class UrlConfig:
    # ... existing fields ...
    user_agent: str | None = None  # Optional per-URL override
```

### Common User-Agent Examples

```yaml
# Browser-like (for strict WAFs)
default_user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Bot-friendly with contact info
default_user_agent: "WebStatusPi/1.0 (+https://example.com/monitoring)"

# Generic monitoring tool
default_user_agent: "HealthCheck/1.0"
```

## Files to Modify

- `webstatuspi/config.py` - Add `default_user_agent` to MonitorConfig, `user_agent` to UrlConfig
- `webstatuspi/monitor.py` - Use configured User-Agent in `check_url()`
- `config.example.yaml` - Add User-Agent examples
- `README.md` - Document User-Agent configuration
- `tests/test_config.py` - Add tests for User-Agent config validation
- `tests/test_monitor.py` - Add tests verifying User-Agent is applied

## Dependencies

None - uses existing stdlib `urllib`

## Follow-up Tasks

None

## Progress Log

(empty)

## Learnings

(empty)
