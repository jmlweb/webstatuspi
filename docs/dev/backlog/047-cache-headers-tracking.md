# Task #047: Cache Headers Tracking

## Metadata
- **Status**: pending
- **Priority**: P4
- **Slice**: Core, Database, API
- **Created**: 2026-01-25
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user, I want to see cache-related headers so I can verify CDN caching is working and monitor cache behavior.

**Acceptance Criteria**:
- [ ] Add `cache_control: str | None` field to `CheckResult`
- [ ] Add `cache_age: int | None` field to `CheckResult`
- [ ] Add columns to `checks` table (migration)
- [ ] Extract `Cache-Control` and `Age` headers
- [ ] Include in `/status` API response
- [ ] Unit tests

## Implementation Notes

### Header Extraction

```python
cache_control = response.headers.get("Cache-Control")
age_header = response.headers.get("Age")
cache_age = int(age_header) if age_header else None
```

### Database Migration

```sql
ALTER TABLE checks ADD COLUMN cache_control TEXT;
ALTER TABLE checks ADD COLUMN cache_age INTEGER;
```

### Value

- Verify CDN caching is working
- Detect stale content issues
- Monitor cache hit rates indirectly (via Age header)

### Performance Impact

- CPU: <0.1% (headers already available)
- RAM: 0 bytes
- Storage: ~50 bytes per check

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
