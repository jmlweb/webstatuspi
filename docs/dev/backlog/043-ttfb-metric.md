# Task #043: Time to First Byte (TTFB) Metric

## Metadata
- **Status**: in_progress
- **Priority**: P3
- **Slice**: Core, Database, API
- **Created**: 2026-01-25
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user, I want to see the Time to First Byte (TTFB) for each URL check so I can identify server-side processing delays vs network latency.

**Acceptance Criteria**:
- [x] Add `ttfb_ms: int | None` field to `CheckResult` dataclass in `models.py`
- [x] Add `ttfb_ms INTEGER` column to `checks` table (migration)
- [x] Measure TTFB in HTTP checker (time between request and first byte)
- [x] Store TTFB in database
- [x] Include `ttfb_ms` in `/history` API response
- [x] Unit tests for TTFB measurement

## Implementation Notes

### TTFB Measurement

Measure time from request initiation until first byte of response:

```python
start = time.perf_counter()
response = opener.open(request, timeout=timeout)
# Read first byte to get TTFB
first_byte = response.read(1)
ttfb_ms = int((time.perf_counter() - start) * 1000)
# Continue reading rest of response
body = first_byte + response.read()
```

### Database Migration

```sql
ALTER TABLE checks ADD COLUMN ttfb_ms INTEGER;
```

### Value

- Detects server-side processing delays vs network latency
- Identifies CDN/proxy performance issues
- Helps debug slow backend processing

### Performance Impact

- CPU: <0.1% (single timestamp)
- RAM: 0 bytes
- Storage: 4 bytes per check

## Files to Modify

- `webstatuspi/models.py` - Add field to CheckResult
- `webstatuspi/database.py` - Add column, update queries
- `webstatuspi/checker.py` - Measure TTFB
- `webstatuspi/api.py` - Include in response
- `tests/test_checker.py` - Unit tests

## Dependencies

None

## Progress Log

### 2026-01-25: Implementation Complete

- Added `ttfb_ms: int | None` field to `CheckResult` dataclass in `models.py`
- Added database migration for `ttfb_ms INTEGER` column in `database.py`
- Modified `check_url()` in `monitor.py` to measure TTFB by reading first byte
- Updated `insert_check()` and `get_history()` to handle ttfb_ms
- Added `ttfb_ms` to `/history/<name>` API response in `api.py`
- Added 6 unit tests for TTFB measurement in `test_monitor.py`
- All 405 tests passing, mypy clean
