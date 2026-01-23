# Task #029: DNS Monitoring

## Metadata
- **Status**: done
- **Priority**: P4
- **Slice**: Core, Config, Database
- **Created**: 2026-01-22
- **Started**: 2026-01-22
- **Completed**: 2026-01-22
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a system administrator, I want to monitor DNS resolution for domain names so that I can detect DNS propagation issues, DNS server failures, or misconfigured DNS records.

**Acceptance Criteria**:
- [x] Config schema supports `dns` section for DNS monitoring
- [x] DNS check resolves domain name and measures resolution time
- [x] Supports A and AAAA record types
- [x] Optional: Verify resolved IP matches expected value
- [x] Resolution success/failure stored in database
- [x] DNS checks integrated into existing monitor loop
- [x] Unit tests for DNS resolution logic
- [x] Documentation added to README.md with examples

## Implementation Notes

### Config Schema Addition

```yaml
urls:
  - name: "DNS_MAIN"
    type: dns
    host: "example.com"
    record_type: A  # Optional: A, AAAA, MX, CNAME (default: A)
    expected_ip: "192.0.2.1"  # Optional: verify resolved IP matches
    
  - name: "DNS_API"
    type: dns
    host: "api.example.com"
    record_type: AAAA
```

### DNS Check Implementation

Use stdlib `socket` module:
```python
import socket

start = time.monotonic()
try:
    # Resolve hostname
    ip = socket.gethostbyname(hostname)  # A record
    # Or use getaddrinfo for AAAA, MX, etc.
    elapsed_ms = int((time.monotonic() - start) * 1000)
    is_up = True
    
    # Optional: verify expected IP
    if expected_ip and ip != expected_ip:
        is_up = False
        error_message = f"Resolved {ip} but expected {expected_ip}"
except socket.gaierror:
    elapsed_ms = int((time.monotonic() - start) * 1000)
    is_up = False
    error_message = "DNS resolution failed"
```

### Record Types

Support common DNS record types:
- `A` (IPv4) - via `socket.gethostbyname()`
- `AAAA` (IPv6) - via `socket.getaddrinfo()`
- `MX` - requires `dnspython` library (add dependency?)
- `CNAME` - requires `dnspython` library (add dependency?)

**Decision**: Start with A and AAAA only (stdlib), add MX/CNAME later if needed.

### Database Compatibility

- Reuse existing `checks` table schema
- `status_code` will be None for DNS checks
- `response_time_ms` stores resolution time
- `is_up` indicates resolution success/failure
- `url` field stores "dns://hostname" for consistency
- `error_message` stores resolution errors or IP mismatch

### URL Format

For DNS checks, construct URL as:
- `url: "dns://hostname"` (for API consistency)

### Performance Impact

- Very lightweight (DNS lookup is fast)
- Uses stdlib `socket` (no dependencies)
- No HTTP overhead
- DNS caching handled by OS

## Files to Modify

**Modified Files**:
- `webstatuspi/config.py` - Add `type`, `record_type`, `expected_ip` fields to UrlConfig
- `webstatuspi/monitor.py` - Add `check_dns()` function, update monitor loop
- `config.example.yaml` - Add DNS monitoring examples
- `README.md` - Document DNS monitoring
- `tests/test_config.py` - Add tests for DNS config validation
- `tests/test_monitor.py` - Add tests for DNS checks

## Dependencies

None - uses stdlib `socket` module (A and AAAA records only)

## Follow-up Tasks

- Future: Add MX/CNAME support (requires `dnspython` dependency)

## Progress Log

- 2026-01-22: Added DnsConfig dataclass with host/record_type/expected_ip
- 2026-01-22: Implemented check_dns() with gethostbyname (A) and getaddrinfo (AAAA)
- 2026-01-22: Updated check_target() dispatcher to handle DNS
- 2026-01-22: Updated Config to include dns list with all_targets property
- 2026-01-22: Added comprehensive tests for DnsConfig and check_dns
- 2026-01-22: Updated README.md with DNS monitoring documentation
- 2026-01-22: Updated config.example.yaml with DNS examples

## Learnings

- Used socket.gethostbyname for A records, socket.getaddrinfo for AAAA
- MX/CNAME would require dnspython library - kept out of scope for simplicity
