# Task #045: Redirect Tracking

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: Core, Database, API
- **Created**: 2026-01-25
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user, I want to track redirect chains so I can detect redirect loops, inefficient redirect chains, and verify redirects terminate at expected URLs.

**Acceptance Criteria**:
- [ ] Add `redirect_count: int` field to `CheckResult` (default 0)
- [ ] Add `final_url: str | None` field to `CheckResult`
- [ ] Add columns to `checks` table (migration)
- [ ] Count redirects using existing `_RedirectHandler`
- [ ] Store final URL after all redirects
- [ ] Include in `/status` API response
- [ ] Unit tests for redirect counting

## Implementation Notes

### Redirect Handler Enhancement

Modify existing `_RedirectHandler` to count redirects:

```python
class _RedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        self.redirect_count = 0
        self.final_url = None

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirect_count += 1
        self.final_url = newurl
        return super().redirect_request(req, fp, code, msg, headers, newurl)
```

### Database Migration

```sql
ALTER TABLE checks ADD COLUMN redirect_count INTEGER DEFAULT 0;
ALTER TABLE checks ADD COLUMN final_url TEXT;
```

### Value

- Detect redirect loops (misconfiguration)
- Identify inefficient redirect chains (http -> https -> www -> canonical)
- Verify redirects terminate at expected URL
- Alert on excessive redirects (> 3-5)

### Performance Impact

- CPU: <0.1% (simple counter)
- RAM: 0 bytes
- Storage: ~104 bytes per check

## Files to Modify

- `webstatuspi/models.py` - Add fields to CheckResult
- `webstatuspi/database.py` - Add columns, update queries
- `webstatuspi/checker.py` - Enhance redirect handler
- `webstatuspi/api.py` - Include in response
- `tests/test_checker.py` - Unit tests

## Dependencies

None

## Progress Log

(empty)
