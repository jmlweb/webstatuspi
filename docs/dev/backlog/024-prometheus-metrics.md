# Task #024: Prometheus Metrics Endpoint

## Metadata
- **Status**: pending
- **Priority**: P2 - Next
- **Slice**: API
- **Created**: 2026-01-22
- **Started**: -
- **Completed**: -
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a DevOps engineer, I want to expose monitoring metrics in Prometheus format so that I can integrate WebStatusPi with my existing Prometheus/Grafana monitoring stack and create unified dashboards.

**Acceptance Criteria**:
- [ ] New `/metrics` endpoint returns Prometheus text format
- [ ] Exposes key metrics: uptime percentage, response time (avg/min/max), check count, failure count
- [ ] Metrics follow Prometheus naming conventions (snake_case, units in suffix)
- [ ] Each URL has its own metric labels (url_name, url)
- [ ] Endpoint is lightweight (no database queries beyond existing API)
- [ ] Documentation added to README.md with example queries
- [ ] Unit tests verify Prometheus format compliance

## Implementation Notes

### Prometheus Format

Prometheus uses a simple text format:
```
# HELP metric_name Description
# TYPE metric_name type
metric_name{label="value"} value timestamp
```

### Metrics to Expose

1. **webstatuspi_uptime_percentage** (gauge)
   - Description: Uptime percentage for the last 24 hours
   - Labels: `url_name`, `url`
   - Value: 0.0-100.0

2. **webstatuspi_response_time_ms** (gauge)
   - Description: Response time metrics
   - Labels: `url_name`, `url`, `type` (avg|min|max)
   - Value: milliseconds

3. **webstatuspi_checks_total** (counter)
   - Description: Total number of checks performed
   - Labels: `url_name`, `url`, `status` (success|failure)
   - Value: count

4. **webstatuspi_last_check_timestamp** (gauge)
   - Description: Unix timestamp of last check
   - Labels: `url_name`, `url`
   - Value: Unix timestamp

### Architecture

- Reuse existing `get_latest_status()` query from database
- Format data as Prometheus text in `api.py`
- No new database queries needed (uses existing API data)
- Thread-safe (read-only operation)

### Performance

- Zero overhead: formats existing in-memory data
- No additional database queries
- Minimal CPU/memory impact

## Files to Modify

**Modified Files**:
- `webstatuspi/api.py` - Add `/metrics` endpoint handler
- `README.md` - Add Prometheus integration section
- `tests/test_api.py` - Add tests for Prometheus format

## Dependencies

None - uses existing infrastructure

## Follow-up Tasks

None

## Progress Log

(To be filled during implementation)

## Learnings

(To be filled during implementation)
