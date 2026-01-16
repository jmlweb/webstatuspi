# Task #003: Monitor Loop with Threading

## Metadata
- **Status**: completed
- **Priority**: P1 - Active
- **Slice**: Core
- **Created**: 2026-01-16
- **Started**: 2026-01-17
- **Completed**: 2026-01-17
- **Blocked by**: - (dependencies #001, #002 completed)

## Vertical Slice Definition

**User Story**: As a monitoring system, I want to periodically check URL health status and store results.

**Acceptance Criteria**:
- [x] Poll each URL at its configured interval
- [x] Use threading for concurrent URL checks
- [x] Measure response time accurately
- [x] Detect HTTP status codes and connection errors
- [x] Store results in database
- [x] Run periodic cleanup of old checks (based on `retention_days` config)
- [x] Handle individual URL failures without stopping others
- [x] Support graceful shutdown signal

## Implementation Notes

### Threading Strategy
```python
# Option A: ThreadPoolExecutor (simpler)
from concurrent.futures import ThreadPoolExecutor

# Option B: Individual threads per URL (more control over intervals)
# Each URL gets its own thread with sleep(interval)
```

### Check Logic
```python
def check_url(url_config: UrlConfig) -> CheckResult:
    start = time.monotonic()
    try:
        response = urllib.request.urlopen(url, timeout=timeout)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return CheckResult(
            url_name=url_config.name,
            url=url_config.url,
            status_code=response.status,
            response_time_ms=elapsed_ms,
            is_up=200 <= response.status < 400,
            error_message=None
        )
    except Exception as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return CheckResult(..., is_up=False, error_message=str(e))
```

### Cleanup Strategy
- Run cleanup after each check cycle (or every N cycles to reduce overhead)
- Delete checks older than `retention_days` from config (default: 7 days)
- Only delete from `checks` table (preserve `stats` table)
- Use parameterized query: `DELETE FROM checks WHERE timestamp < datetime('now', '-' || ? || ' days')`

### Pi 1B+ Constraints
- Limit thread pool size (max 2-4 threads)
- Use `urllib.request` instead of `requests` (lighter)
- Consider staggered start times to avoid burst
- Run cleanup periodically (not on every check) to minimize SD card writes

## Files to Modify
- `webstatuspi/monitor.py` (create) - Monitor loop and URL checking
- `webstatuspi/models.py` (update) - CheckResult already exists from #002

## Dependencies
- #001 Config loader (for URL list and intervals)
- #002 Database layer (for storing results)

## Progress Log
- [2026-01-17 14:00] Started task
- [2026-01-17 14:15] Created `webstatuspi/monitor.py` with:
  - `check_url()` function using `urllib.request` (lightweight)
  - `Monitor` class with `ThreadPoolExecutor` (max 3 workers)
  - Staggered initial check times to avoid burst
  - Graceful shutdown via `threading.Event`
  - Periodic cleanup every 100 cycles
- [2026-01-17 14:20] Created `tests/test_monitor.py` with 21 tests
- [2026-01-17 14:25] All 46 tests passing
- [2026-01-17 14:30] Task completed

## Learnings
Transferred to LEARNINGS.md as L008, L009, L010
