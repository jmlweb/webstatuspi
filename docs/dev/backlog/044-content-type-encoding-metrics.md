# Task #044: Content-Type and Content-Encoding Metrics

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: Core, Database, API
- **Created**: 2026-01-25
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user, I want to see the Content-Type and Content-Encoding of responses so I can detect unexpected format changes and verify compression is enabled.

**Acceptance Criteria**:
- [ ] Add `content_type: str | None` field to `CheckResult` dataclass
- [ ] Add `content_encoding: str | None` field to `CheckResult` dataclass
- [ ] Add columns to `checks` table (migration)
- [ ] Extract headers in HTTP checker
- [ ] Store in database
- [ ] Include in `/status` API response
- [ ] Unit tests

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

## Files to Modify

- `webstatuspi/models.py` - Add fields to CheckResult
- `webstatuspi/database.py` - Add columns, update queries
- `webstatuspi/checker.py` - Extract headers
- `webstatuspi/api.py` - Include in response
- `tests/test_checker.py` - Unit tests

## Dependencies

None

## Progress Log

(empty)
