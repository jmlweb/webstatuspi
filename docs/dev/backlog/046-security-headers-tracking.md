# Task #046: Security Headers Tracking

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: Core, Database, API
- **Created**: 2026-01-25
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user, I want to track presence of key security headers so I can perform basic security audits and detect configuration regressions.

**Acceptance Criteria**:
- [ ] Add `has_hsts: bool` field to `CheckResult` (default False)
- [ ] Add `has_x_frame_options: bool` field to `CheckResult` (default False)
- [ ] Add `has_x_content_type_options: bool` field to `CheckResult` (default False)
- [ ] Add columns to `checks` table (migration, stored as INTEGER 0/1)
- [ ] Check header presence in HTTP checker
- [ ] Include in `/status` API response
- [ ] Unit tests

## Implementation Notes

### Header Detection

```python
has_hsts = response.headers.get("Strict-Transport-Security") is not None
has_x_frame_options = response.headers.get("X-Frame-Options") is not None
has_x_content_type_options = response.headers.get("X-Content-Type-Options") is not None
```

### Database Migration

```sql
ALTER TABLE checks ADD COLUMN has_hsts INTEGER DEFAULT 0;
ALTER TABLE checks ADD COLUMN has_x_frame_options INTEGER DEFAULT 0;
ALTER TABLE checks ADD COLUMN has_x_content_type_options INTEGER DEFAULT 0;
```

### Tracked Headers

| Header | Purpose |
|--------|---------|
| `Strict-Transport-Security` (HSTS) | Forces HTTPS connections |
| `X-Frame-Options` | Prevents clickjacking |
| `X-Content-Type-Options` | Prevents MIME sniffing |

### Value

- Basic security audit capability
- Detect configuration regressions (headers removed)
- Compliance monitoring (PCI-DSS, GDPR)

### Performance Impact

- CPU: <0.1% (headers already available)
- RAM: 0 bytes
- Storage: 3 bytes per check

## Files to Modify

- `webstatuspi/models.py` - Add fields to CheckResult
- `webstatuspi/database.py` - Add columns, update queries
- `webstatuspi/checker.py` - Check header presence
- `webstatuspi/api.py` - Include in response
- `tests/test_checker.py` - Unit tests

## Dependencies

None

## Progress Log

(empty)
