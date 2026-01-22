# Task #026: SSL Certificate Expiration Monitoring

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: Core, Config, Database, API
- **Created**: 2026-01-22
- **Started**: -
- **Completed**: -
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a system administrator, I want to be alerted when SSL certificates are about to expire so that I can renew them before they cause service outages.

**Acceptance Criteria**:
- [ ] SSL certificate expiration date extracted from HTTPS URLs
- [ ] Days until expiration calculated and stored
- [ ] Certificate expiration exposed in `/status` API endpoint
- [ ] Configurable warning threshold (default: 30 days)
- [ ] Expired certificates treated as check failure
- [ ] Certificate issuer and subject stored for reference
- [ ] Unit tests for certificate parsing and expiration calculation
- [ ] Documentation added to README.md

## Implementation Notes

### SSL Certificate Extraction

Use Python stdlib `ssl` module:
```python
import ssl
import socket

# Get certificate
context = ssl.create_default_context()
with socket.create_connection((hostname, 443), timeout=10) as sock:
    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
        cert = ssock.getpeercert()
        # cert is a dict with 'notAfter', 'subject', 'issuer'
```

### Database Schema Addition

Add to `checks` table:
- `ssl_days_until_expiry INTEGER` (nullable, only for HTTPS URLs)
- `ssl_issuer TEXT` (nullable)
- `ssl_subject TEXT` (nullable)

### API Changes

Add to `UrlStatus` model:
- `ssl_days_until_expiry: int | None`
- `ssl_issuer: str | None`
- `ssl_subject: str | None`

### Warning Threshold

Config option:
```yaml
monitor:
  ssl_warning_days: 30  # Alert if cert expires within N days
```

### Performance Impact

- Only for HTTPS URLs (no overhead for HTTP)
- Single SSL handshake per check (already done for HTTPS)
- Certificate parsing is lightweight
- No additional network requests

### Expiration Logic

- If `ssl_days_until_expiry <= 0`: Treat as failure (cert expired)
- If `ssl_days_until_expiry <= warning_threshold`: Log warning
- Store expiration info even if cert is valid

## Files to Modify

**Modified Files**:
- `webstatuspi/config.py` - Add `ssl_warning_days` to MonitorConfig
- `webstatuspi/monitor.py` - Extract SSL cert info for HTTPS URLs
- `webstatuspi/models.py` - Add SSL fields to CheckResult and UrlStatus
- `webstatuspi/database.py` - Add SSL columns to schema, update queries
- `webstatuspi/api.py` - Expose SSL info in API responses
- `config.example.yaml` - Add SSL warning example
- `README.md` - Document SSL monitoring
- `tests/test_monitor.py` - Add SSL certificate tests

## Dependencies

None - uses stdlib `ssl` and `socket` modules

## Follow-up Tasks

None

## Progress Log

(To be filled during implementation)

## Learnings

(To be filled during implementation)
