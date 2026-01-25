# Task #048: Resolved IP Address Tracking

## Metadata
- **Status**: pending
- **Priority**: P4
- **Slice**: Core, Database, API
- **Created**: 2026-01-25
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user, I want to see the IP address that the hostname resolved to so I can detect IP changes, debug DNS issues, and track geographic routing changes.

**Acceptance Criteria**:
- [ ] Add `resolved_ip: str | None` field to `CheckResult`
- [ ] Add column to `checks` table (migration)
- [ ] Extract IP address using `socket.getpeername()` after connection
- [ ] Include in `/status` API response
- [ ] Unit tests

## Implementation Notes

### IP Extraction

The IP address is available from the socket after connection:

```python
# After establishing connection
sock = response.fp.raw._sock
if sock:
    resolved_ip = sock.getpeername()[0]
```

Alternative approach using custom HTTPHandler to capture during connection.

### Database Migration

```sql
ALTER TABLE checks ADD COLUMN resolved_ip TEXT;
```

### Value

- Detect IP changes (failover, CDN routing)
- Debug DNS issues
- Detect potential DNS hijacking
- Track geographic routing changes

### Performance Impact

- CPU: <0.1% (data already available during connection)
- RAM: 0 bytes
- Storage: ~15 bytes per check

## Files to Modify

- `webstatuspi/models.py` - Add field to CheckResult
- `webstatuspi/database.py` - Add column, update queries
- `webstatuspi/checker.py` - Extract IP address
- `webstatuspi/api.py` - Include in response
- `tests/test_checker.py` - Unit tests

## Dependencies

None

## Progress Log

(empty)
