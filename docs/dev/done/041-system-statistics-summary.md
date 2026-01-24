# Task #041: System Statistics Summary

## Metadata
- **Status**: completed
- **Priority**: P1 - Active
- **Slice**: Backend, API
- **Created**: 2026-01-24
- **Started**: 2026-01-24
- **Completed**: 2026-01-24
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user, I want to see aggregated system statistics so that I can quickly assess overall system health.

**Acceptance Criteria**:
- [x] Extend `/status` endpoint with `summary` object
- [x] Include: total_services, services_up, services_down
- [x] Include: average_uptime_24h (percentage)
- [x] Include: average_latency_ms (24h average)
- [x] Backward compatible (existing fields unchanged)

## Implementation Notes

### Extend `/status` response

```python
@app.get("/status")
async def get_status():
    statuses = get_all_statuses()

    # Calculate summary
    total = len(statuses)
    up = sum(1 for s in statuses if s["status"] == "UP")
    down = total - up

    # Get 24h metrics from database
    avg_uptime = calculate_average_uptime_24h()
    avg_latency = calculate_average_latency_24h()

    return {
        "urls": statuses,
        "summary": {
            "total_services": total,
            "services_up": up,
            "services_down": down,
            "average_uptime_24h": round(avg_uptime, 2),
            "average_latency_ms": round(avg_latency, 1)
        }
    }
```

### SQL for 24h metrics

```sql
-- Average uptime (percentage of UP checks)
SELECT
    (COUNT(CASE WHEN status = 'UP' THEN 1 END) * 100.0 / COUNT(*)) as uptime
FROM checks
WHERE timestamp > datetime('now', '-24 hours');

-- Average latency
SELECT AVG(latency_ms) as avg_latency
FROM checks
WHERE timestamp > datetime('now', '-24 hours')
AND status = 'UP';
```

## Files to Modify

- `webstatuspi/api.py` - Extend /status endpoint
- `webstatuspi/database.py` - Add aggregate query functions

## Dependencies

None

## Progress Log

- [2026-01-24 12:00] Started task
- [2026-01-24 12:30] Task completed - added average_uptime_24h and average_latency_ms to summary
