# Task #032: Latency Degradation Alerts

## Metadata
- **Status**: completed
- **Priority**: P2
- **Slice**: Core, Config, Alerts
- **Created**: 2026-01-23
- **Started**: 2026-01-23
- **Completed**: 2026-01-23
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a system administrator, I want to receive alerts when a service's response time exceeds a threshold for a sustained period so that I can detect performance degradation before it causes a complete outage.

**Acceptance Criteria**:
- [x] Config schema supports latency threshold per URL
- [x] Config schema supports sustained period (consecutive checks or time window)
- [x] Alert is triggered when latency exceeds threshold for the configured period
- [x] Alert is cleared when latency returns to normal
- [x] Latency alerts use existing webhook infrastructure
- [x] New event types: `latency_high` and `latency_normal`
- [x] Unit tests for latency threshold logic
- [x] Documentation added to README.md with examples

## Implementation Notes

### Config Schema Addition

```yaml
urls:
  - name: "critical-api"
    url: "https://api.example.com/health"
    latency_threshold_ms: 2000        # Alert if response time exceeds this
    latency_consecutive_checks: 3     # Must exceed threshold N times in a row

  - name: "payment-api"
    url: "https://payments.example.com"
    latency_threshold_ms: 1000
    latency_window_minutes: 5         # Alternative: average over time window
```

### Two Approaches

**Approach A: Consecutive Checks** (simpler)
- Alert after N consecutive checks exceed threshold
- Easier to implement, less database queries
- May miss intermittent spikes

**Approach B: Time Window Average** (more robust)
- Alert if average latency over X minutes exceeds threshold
- Requires querying recent checks from database
- More accurate but more complex

**Recommendation**: Start with Approach A (consecutive checks), add window-based later if needed.

### Implementation in alerter.py

Add latency state tracking alongside up/down state:

```python
@dataclass
class UrlState:
    is_up: bool | None = None
    consecutive_slow: int = 0
    is_latency_alert_active: bool = False

def check_latency_alert(
    self,
    url_config: UrlConfig,
    response_time_ms: int,
    state: UrlState
) -> Alert | None:
    """Check if latency alert should be triggered or cleared."""
    if url_config.latency_threshold_ms is None:
        return None

    threshold = url_config.latency_threshold_ms
    required = url_config.latency_consecutive_checks or 3

    if response_time_ms > threshold:
        state.consecutive_slow += 1
        if state.consecutive_slow >= required and not state.is_latency_alert_active:
            state.is_latency_alert_active = True
            return Alert(event="latency_high", ...)
    else:
        if state.is_latency_alert_active:
            state.is_latency_alert_active = False
            state.consecutive_slow = 0
            return Alert(event="latency_normal", ...)
        state.consecutive_slow = 0

    return None
```

### Webhook Payload for Latency Alerts

```json
{
  "event": "latency_high",
  "url": {
    "name": "critical-api",
    "url": "https://api.example.com/health"
  },
  "latency": {
    "current_ms": 2500,
    "threshold_ms": 2000,
    "consecutive_checks": 3
  },
  "timestamp": "2026-01-23T10:30:00Z"
}
```

### Config Changes

Add to `UrlConfig` dataclass:
```python
@dataclass
class UrlConfig:
    # ... existing fields ...
    latency_threshold_ms: int | None = None
    latency_consecutive_checks: int = 3
```

### Integration with Monitor Loop

After each check, call alerter with response time:
```python
# In monitor.py check cycle
result = check_url(url_config)
alerter.process_result(url_config, result)  # Existing UP/DOWN logic
alerter.check_latency(url_config, result.response_time_ms)  # New latency logic
```

## Files to Modify

- `webstatuspi/config.py` - Add latency threshold fields to UrlConfig
- `webstatuspi/alerter.py` - Add latency alert logic, new event types
- `webstatuspi/monitor.py` - Pass response time to alerter
- `config.example.yaml` - Add latency threshold examples
- `README.md` - Document latency alerts
- `tests/test_alerter.py` - Add tests for latency alert logic
- `tests/test_config.py` - Add tests for latency config validation

## Dependencies

None

## Follow-up Tasks

- Add time-window based averaging (Approach B) for more sophisticated alerting
- Add latency percentile alerts (P95 > threshold)

## Progress Log

### 2026-01-23 - Implementation Complete

- ✅ Added `latency_threshold_ms` and `latency_consecutive_checks` fields to `UrlConfig`
- ✅ Added latency state tracking to `StateTracker` (consecutive_slow, is_latency_alert_active)
- ✅ Implemented `check_latency_alert()` method in `Alerter` class
- ✅ Implemented `_send_latency_webhook()` method for latency-specific webhook payloads
- ✅ Integrated latency checking in `__init__.py` callback to monitor both up/down and latency alerts
- ✅ Updated `config.example.yaml` with latency threshold examples
- ✅ Updated `README.md` with comprehensive latency alerts documentation
- ✅ Added comprehensive unit tests for latency alert logic (test_alerter.py)
- ✅ Added unit tests for latency config validation (test_config.py)

**Implementation Notes:**
- Used Approach A (consecutive checks) as recommended in task notes
- Latency alerts use same webhook infrastructure as up/down alerts
- New event types: `latency_high` and `latency_normal`
- Latency alerts respect cooldown_seconds setting to prevent spam
- Counter resets when latency returns to normal before alert threshold

## Learnings

(empty)
