# Task #021: HTTP Headers Capture (Server, Status Text)

## Metadata
- **Status**: completed
- **Priority**: P3 - Low
- **Slice**: Core, Database, API
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a system administrator, I want to see HTTP server information (Server header, status text) so that I can debug infrastructure changes and have more readable status information.

**Acceptance Criteria**:
- [x] Server header captured from HTTP responses and stored in database
- [x] Status text (reason phrase) captured and stored in database
- [x] New fields included in CheckResult and UrlStatus models
- [x] API responses include server_header and status_text
- [x] Unit tests added for header capture
- [x] Performance impact verified (should be negligible)

## Implementation Notes

### Data Capture (minimal overhead)
These headers are already available in HTTP responses, just need to extract and store:

- `server_header`: Value of `Server` header (e.g., "nginx/1.18.0", "Apache/2.4.41")
- `status_text`: HTTP status reason phrase (e.g., "OK", "Service Unavailable", "Not Found")

### Implementation Pattern

Similar to `content_length` implementation in #019:

1. **Capture in monitor.py**:
   ```python
   # In check_url() function, after getting response
   server_header = response.headers.get("Server")
   status_text = response.reason  # or response.msg for urllib
   ```

2. **Store in CheckResult**:
   - Add `server_header: str | None` field
   - Add `status_text: str | None` field

3. **Database Schema**:
   - Add `server_header TEXT` column to `checks` table (nullable)
   - Add `status_text TEXT` column to `checks` table (nullable)
   - Migration: `ALTER TABLE checks ADD COLUMN server_header TEXT`
   - Migration: `ALTER TABLE checks ADD COLUMN status_text TEXT`

4. **UrlStatus Model**:
   - Add `server_header: str | None` (from most recent check)
   - Add `status_text: str | None` (from most recent check)

### Performance Considerations
- Headers are already in response object (no extra network call)
- String storage is minimal (~50-200 bytes per check)
- No CPU overhead (simple string extraction)
- With 7-day retention and 10 URLs at 60s interval: ~604,800 checks = ~30-120MB additional storage (acceptable)

### Use Cases
- **Server header**: Detect infrastructure changes (e.g., nginx → Apache migration)
- **Status text**: More readable than status codes (e.g., "Service Unavailable" vs "503")

### API Changes
- Update `CheckResult` model in `models.py`
- Update `UrlStatus` model in `models.py`
- Update `_url_status_to_dict()` in `api.py` to serialize new fields
- Update `get_latest_status()` query in `database.py` to include new columns

### Dashboard Display (Optional)
- Show server header in tooltip or metadata section
- Use status text instead of/in addition to status code for readability

## Files to Modify

- `webstatuspi/models.py` - Add server_header and status_text to CheckResult and UrlStatus
- `webstatuspi/database.py` - Add columns to schema, update queries, add migration
- `webstatuspi/monitor.py` - Capture Server header and status text from responses
- `webstatuspi/api.py` - Serialize new fields in JSON responses
- `webstatuspi/_dashboard.py` - Display server info in UI (optional)
- `tests/test_monitor.py` - Add tests for header capture
- `tests/test_database.py` - Add tests for new columns

## Dependencies

None - uses existing infrastructure (similar to content_length in #019)

## Performance Impact Estimate

- **CPU**: <0.1% (simple string extraction)
- **RAM**: +~50-200 bytes per check record (negligible)
- **Storage**: +~30-120MB for 7-day retention with 10 URLs (acceptable)
- **Network**: No impact (headers already in response)

**Conclusion**: Negligible impact, safe to implement.

## References

- Task #019 (Extended Metrics) - Similar pattern for capturing response headers
- Task #020 (Response Time Percentiles) - Can be implemented in parallel

## Progress Log

- [2026-01-21] Task created based on metrics analysis
- [2026-01-21] Task completed - implemented header capture, database migration, tests

## Learnings

### Implementation Details

1. **HTTP Header Extraction**: Used `response.headers.get("Server")` for Server header and `getattr(response, "reason", None)` for status text (reason phrase) from urllib responses.

2. **Database Migration**: Added automatic column migration in `init_db()` that checks for missing columns and adds them using `ALTER TABLE`. This pattern ensures backward compatibility with existing databases.

3. **Test Coverage**: Added 22 comprehensive tests covering:
   - Header capture from successful responses
   - Header capture from HTTPError responses
   - None handling when headers are missing
   - Various server header values (nginx, Apache, cloudflare, IIS)
   - Database storage and retrieval
   - Schema migration verification

4. **Performance Impact**: Negligible - headers are already in the response object, no additional network calls required. Storage overhead is minimal (~50-200 bytes per check).

5. **Integration with Task #020**: Task was implemented alongside Task #020 (Response Time Percentiles). Both tasks added fields to the same models and database schema without conflicts.
