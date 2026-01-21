# Task #019: Extended Metrics

## Metadata
- **Status**: completed
- **Priority**: P1 - Active
- **Slice**: Core, Database, API
- **Created**: 2026-01-21
- **Started**: 2026-01-21
- **Completed**: 2026-01-21
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a system administrator, I want to see detailed performance metrics (average/min/max response times, consecutive failures, content size) so that I can better understand service health trends and identify performance degradation patterns.

**Acceptance Criteria**:
- [x] Database queries calculate avg_response_time_24h, min_response_time_24h, max_response_time_24h from existing data
- [x] Database queries calculate consecutive_failures and last_downtime from existing data
- [x] Content-Length header captured from HTTP responses and stored in database
- [x] Internet connectivity status exposed in `/status` API endpoint
- [x] All new metrics included in UrlStatus model and API responses
- [x] Dashboard updated to display new metrics where appropriate
- [x] Unit tests added for new metrics calculations
- [x] Performance impact verified on Pi 1B+ (no significant overhead)

## Implementation Notes

### Derived Metrics (SQL-only, zero overhead)
These metrics can be calculated from existing `checks` table data using SQL aggregations:
- `avg_response_time_24h`: `AVG(response_time_ms)` for last 24h
- `min_response_time_24h`: `MIN(response_time_ms)` for last 24h
- `max_response_time_24h`: `MAX(response_time_ms)` for last 24h
- `consecutive_failures`: Count of consecutive failed checks from most recent
- `last_downtime`: Timestamp of most recent failed check

### Data Capture (minimal overhead)
- `content_length`: Extract from `response.headers.get('Content-Length')` in monitor.py:173
- `internet_status`: Already tracked in Monitor class (monitor.py:263), expose via API

### Database Schema Change
Add to `checks` table:
- `content_length INTEGER` (nullable, some responses don't include this header)

### API Changes
- Update `UrlStatus` model to include new metrics
- Update `_url_status_to_dict()` in api.py to serialize new fields
- Update `get_latest_status()` query in database.py to calculate derived metrics

### Performance Considerations
- Content-Length is already in response headers (no extra network call)
- SQL aggregations run on indexed columns (checked_at, url_name)
- No new network requests or blocking operations

## Files to Modify
- `webstatuspi/models.py` - Add fields to UrlStatus dataclass
- `webstatuspi/database.py` - Update schema, add content_length column, update queries
- `webstatuspi/monitor.py` - Capture content_length from response headers
- `webstatuspi/api.py` - Expose internet_status, serialize new metrics
- `webstatuspi/_dashboard.py` - Display new metrics in UI
- `tests/test_database.py` - Add tests for new metrics calculations
- `tests/test_monitor.py` - Add tests for content_length capture

## Dependencies
None - uses existing data and infrastructure

## Progress Log
- [2026-01-21 00:00] Started task
- [2026-01-21 00:15] Updated models.py: Added content_length to CheckResult, extended UrlStatus with 6 new metrics fields
- [2026-01-21 00:20] Updated database.py: Added content_length column, schema migration, updated queries with SQL CTEs for derived metrics
- [2026-01-21 00:25] Updated monitor.py: Capture Content-Length from HTTP response headers
- [2026-01-21 00:30] Updated api.py: Serialize all new metrics, expose internet_status in /status endpoint
- [2026-01-21 00:35] Updated _dashboard.py: Display response time stats, consecutive failures warning, content length
- [2026-01-21 00:40] Added 21 new unit tests for metrics calculations and content_length capture
- [2026-01-21 00:45] All 230 tests pass, linting clean
- [2026-01-21 00:50] Task completed - learnings transferred to LEARNINGS.md

## Learnings
(Transferred to LEARNINGS.md as L021 and L022)
