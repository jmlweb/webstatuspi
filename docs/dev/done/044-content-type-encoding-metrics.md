# Task #044: Content-Type and Content-Encoding Metrics

## Metadata
- **Status**: done
- **Priority**: P1 - Active
- **Slice**: Core, Database, API
- **Created**: 2026-01-25
- **Started**: 2026-01-25
- **Completed**: 2026-01-25
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user, I want to see the Content-Type and Content-Encoding of responses so I can detect unexpected format changes and verify compression is enabled.

**Acceptance Criteria**:
- [x] Add `content_type: str | None` field to `CheckResult` dataclass
- [x] Add `content_encoding: str | None` field to `CheckResult` dataclass
- [x] Add columns to `checks` table (migration)
- [x] Extract headers in HTTP checker
- [x] Store in database
- [x] Include in `/status` API response
- [x] Unit tests

## Implementation Notes

### Header Extraction

```python
content_type = response.headers.get("Content-Type")
content_encoding = response.headers.get("Content-Encoding")
```

### Database Migration

```sql
ALTER TABLE checks ADD COLUMN content_type TEXT;
ALTER TABLE checks ADD COLUMN content_encoding TEXT;
```

### Value

- **Content-Type**: Detect unexpected format changes (e.g., JSON API returning HTML error page)
- **Content-Encoding**: Verify server compression is enabled (gzip, br, deflate)

### Performance Impact

- CPU: <0.1% (headers already available)
- RAM: 0 bytes
- Storage: ~40 bytes per check

## Files Modified

- `webstatuspi/models.py` - Added `content_type` and `content_encoding` fields to `CheckResult` and `UrlStatus`
- `webstatuspi/database.py` - Added columns with migration, updated `insert_check`, `get_latest_status`, `get_latest_status_by_name`, and `get_history`
- `webstatuspi/monitor.py` - Extract headers in `check_url` (success and error cases)
- `tests/test_database.py` - Added `TestContentTypeEncodingMetrics` test class (11 tests)
- `tests/test_monitor.py` - Added `TestContentTypeEncodingHeaders` test class (8 tests)

## Dependencies

None

## Progress Log

### 2026-01-25: Started task
### 2026-01-25: Completed implementation
- Added `content_type` and `content_encoding` fields to `CheckResult` dataclass
- Added fields to `UrlStatus` dataclass for API response
- Added database schema migration for new columns
- Updated `insert_check` to store new fields
- Updated `_fetch_latest_status_from_db` to include new fields in SQL query and UrlStatus creation
- Updated `get_latest_status_by_name` to include new fields
- Updated `get_history` to include new fields in CheckResult
- Updated `check_url` to extract Content-Type and Content-Encoding headers (success and HTTPError cases)
- Added 11 database tests for storage, retrieval, migration
- Added 8 monitor tests for header extraction
- All 424 tests pass
