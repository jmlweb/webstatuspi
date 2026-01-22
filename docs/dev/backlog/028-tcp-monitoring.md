# Task #028: TCP Port Monitoring

## Metadata
- **Status**: pending
- **Priority**: P4
- **Slice**: Core, Config, Database
- **Created**: 2026-01-22
- **Started**: -
- **Completed**: -
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a system administrator, I want to monitor TCP port connectivity (e.g., database ports, Redis, custom services) so that I can verify network-level availability beyond HTTP endpoints.

**Acceptance Criteria**:
- [ ] Config schema supports `type: tcp` for non-HTTP monitoring
- [ ] TCP check connects to host:port and measures connection time
- [ ] Connection success/failure stored in database (reusing existing schema)
- [ ] Response time measured as connection establishment time
- [ ] TCP checks integrated into existing monitor loop
- [ ] Unit tests for TCP connection logic
- [ ] Documentation added to README.md with examples

## Implementation Notes

### Config Schema Addition

```yaml
urls:
  - name: "DB_POSTGRES"
    type: tcp
    host: "db.example.com"
    port: 5432
    timeout: 5
    
  - name: "REDIS_CACHE"
    type: tcp
    host: "redis.example.com"
    port: 6379
    timeout: 3
```

### Type Field

Add `type` field to UrlConfig:
- `type: http` (default) - existing HTTP/HTTPS monitoring
- `type: tcp` - TCP port connectivity check

### TCP Check Implementation

Use stdlib `socket` module:
```python
import socket

start = time.monotonic()
try:
    sock = socket.create_connection((host, port), timeout=timeout)
    sock.close()
    elapsed_ms = int((time.monotonic() - start) * 1000)
    is_up = True
except (socket.timeout, OSError):
    elapsed_ms = int((time.monotonic() - start) * 1000)
    is_up = False
```

### Database Compatibility

- Reuse existing `checks` table schema
- `status_code` will be None for TCP checks
- `response_time_ms` stores connection time
- `is_up` indicates connection success/failure
- `url` field stores "tcp://host:port" for consistency

### URL Format

For TCP checks, construct URL as:
- `url: "tcp://host:port"` (for API consistency)

### Performance Impact

- Similar to HTTP checks (network I/O)
- TCP connection is faster than HTTP (no HTTP protocol overhead)
- No additional dependencies (uses stdlib `socket`)

## Files to Modify

**Modified Files**:
- `webstatuspi/config.py` - Add `type` and `port` fields to UrlConfig, update validation
- `webstatuspi/monitor.py` - Add `check_tcp()` function, update monitor loop to handle TCP
- `config.example.yaml` - Add TCP monitoring examples
- `README.md` - Document TCP monitoring
- `tests/test_config.py` - Add tests for TCP config validation
- `tests/test_monitor.py` - Add tests for TCP checks

## Dependencies

None - uses stdlib `socket` module

## Follow-up Tasks

None

## Progress Log

(To be filled during implementation)

## Learnings

(To be filled during implementation)
