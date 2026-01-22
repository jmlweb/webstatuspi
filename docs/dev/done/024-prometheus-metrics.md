# Task #024: Prometheus Metrics Endpoint

## Metadata
- **Status**: completed
- **Priority**: P2 - Next
- **Slice**: API
- **Created**: 2026-01-22
- **Started**: 2026-01-22
- **Completed**: 2026-01-22
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a DevOps engineer, I want to expose monitoring metrics in Prometheus format so that I can integrate WebStatusPi with my existing Prometheus/Grafana monitoring stack and create unified dashboards.

**Acceptance Criteria**:
- [x] New `/metrics` endpoint returns Prometheus text format
- [x] Exposes key metrics: uptime percentage, response time (avg/min/max), check count, failure count
- [x] Metrics follow Prometheus naming conventions (snake_case, units in suffix)
- [x] Each URL has its own metric labels (url_name, url)
- [x] Endpoint is lightweight (no database queries beyond existing API)
- [x] Documentation added to README.md with example queries
- [x] Unit tests verify Prometheus format compliance

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

**2026-01-22**: Implementation completed
- Added `_format_prometheus_metrics()` function to convert UrlStatus objects to Prometheus text format
- Added `_send_text()` helper method for sending plain text responses
- Added `_handle_metrics()` method to handle GET /metrics endpoint
- Implemented proper label escaping for special characters (quotes, backslashes, newlines)
- Added 8 comprehensive unit tests covering all metrics and edge cases
- Updated README.md with Prometheus integration section including:
  - Metrics endpoint documentation
  - Available metrics table
  - Prometheus configuration example
  - Example PromQL queries
  - Grafana dashboard suggestions
- All tests pass (50/50 relevant tests)
- Code passes ruff linting and formatting checks

## Learnings

1. **Prometheus Text Format**: The exposition format requires proper escaping of label values (backslash, quote, newline) to avoid parsing errors. Implemented proper escaping in `_format_prometheus_metrics()`.

2. **Content-Type Header**: Prometheus text format uses `text/plain; version=0.0.4` as the Content-Type to indicate the format version.

3. **Metric Naming**: Following Prometheus best practices:
   - Use snake_case for metric names
   - Include units in suffix (e.g., `_ms`, `_percentage`)
   - Use `_total` suffix for counters
   - Avoid redundant prefixes in labels

4. **Zero Overhead**: The `/metrics` endpoint reuses the existing `get_latest_status()` database query, adding no additional database load. Metrics are computed from existing aggregated data.

5. **Label Cardinality**: With typical deployments monitoring 5-20 URLs, this creates minimal cardinality (4 metric types × 20 URLs = ~80 series), well within Prometheus's capacity.

6. **Test Coverage**: Comprehensive tests cover:
   - Empty database state
   - Single and multiple URLs
   - Label escaping
   - Success/failure count calculation
   - Response time metrics (avg/min/max)
   - Timestamp format validation
