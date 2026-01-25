# Task #049: TLS Version Tracking

## Metadata
- **Status**: pending
- **Priority**: P4
- **Slice**: Core, Database, API
- **Created**: 2026-01-25
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user, I want to see the TLS protocol version used for HTTPS connections so I can perform security audits and ensure compliance.

**Acceptance Criteria**:
- [ ] Add `tls_version: str | None` field to `CheckResult`
- [ ] Add column to `checks` table (migration)
- [ ] Extract TLS version during existing SSL certificate check
- [ ] Include in `/status` API response
- [ ] Unit tests

## Implementation Notes

### TLS Version Extraction

TLS version is available via `ssl.SSLSocket.version()`:

```python
# During SSL certificate extraction (already happening)
with socket.create_connection((hostname, 443), timeout=timeout) as sock:
    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
        tls_version = ssock.version()  # e.g., "TLSv1.3", "TLSv1.2"
        cert = ssock.getpeercert()
```

### Database Migration

```sql
ALTER TABLE checks ADD COLUMN tls_version TEXT;
```

### Value

- Security audit (detect outdated TLS like TLSv1.0, TLSv1.1)
- Monitor TLS upgrades
- Compliance requirements

### Performance Impact

- CPU: <0.1% (data available during existing SSL check)
- RAM: 0 bytes
- Storage: ~10 bytes per check

## Files to Modify

- `webstatuspi/models.py` - Add field to CheckResult
- `webstatuspi/database.py` - Add column, update queries
- `webstatuspi/checker.py` - Extract during SSL check
- `webstatuspi/api.py` - Include in response
- `tests/test_checker.py` - Unit tests

## Dependencies

None

## Progress Log

(empty)
