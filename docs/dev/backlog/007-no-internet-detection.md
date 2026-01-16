# Task #007: NO INTERNET Detection

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: Core
- **Created**: 2026-01-17
- **Started**: -
- **Blocked by**: #003 (needs monitor loop implementation)

## Vertical Slice Definition

**User Story**: As a monitoring system, when all configured URLs fail, I want to detect if the issue is internet connectivity loss and display a single "NO INTERNET" alert instead of multiple individual URL failure alerts.

**Acceptance Criteria**:
- [ ] Detect when all URLs fail in a single check round
- [ ] Verify internet connectivity via DNS lookup when all URLs fail
- [ ] Display "NO INTERNET" message in console when connectivity is lost
- [ ] Skip individual URL failure alerts when "NO INTERNET" is detected
- [ ] Store internet connectivity status for future display/API use
- [ ] Handle connectivity check timeouts gracefully (default 5 seconds)

## Implementation Notes

### Internet Connectivity Check

Use DNS lookup to a reliable server (8.8.8.8) to verify connectivity:

```python
def check_internet_connectivity(timeout: int = 5) -> bool:
    """Check if internet connectivity is available via DNS lookup.
    
    Uses socket (stdlib) to avoid additional dependencies.
    Performs DNS lookup to Google's DNS server (8.8.8.8) and
    attempts TCP connection to port 53 (DNS).
    
    Args:
        timeout: Timeout in seconds for connectivity check.
        
    Returns:
        True if internet connectivity is available, False otherwise.
    """
    import socket
    
    try:
        # Try DNS lookup to Google's DNS server (8.8.8.8)
        socket.gethostbyname('8.8.8.8')
        # Try reverse lookup to verify connectivity
        socket.create_connection(('8.8.8.8', 53), timeout=timeout)
        return True
    except (socket.gaierror, socket.timeout, OSError):
        return False
```

### Detection Logic

In the monitor loop, after all URL checks complete:
- If all URLs failed → check internet connectivity
- If no internet → log "NO INTERNET" alert and skip individual alerts
- If internet available → show normal individual URL failure alerts

### Console Output Format

```
[2026-01-17 10:30:15] ⚠ NO INTERNET - All URLs unavailable
```

Format matches existing check output format for consistency.

### Internet Status State

Maintain global state for internet connectivity status:
- `None`: Unknown (not yet checked)
- `True`: Internet available (last check)
- `False`: No internet (last check)

This state can be queried by:
- Display OLED (future implementation)
- API JSON response (optional enhancement)

### Cases to Handle

1. **All URLs fail + No internet**: Show only "NO INTERNET" alert
2. **All URLs fail + Internet available**: Show normal individual URL failure alerts (service issues)
3. **Some URLs fail**: Show normal individual URL failure alerts (current behavior)

### Pi 1B+ Constraints

- Internet check only runs when all URLs fail (minimal overhead)
- DNS lookup is lightweight and fast (suitable for Pi 1B+)
- Timeout of 5 seconds prevents long blocking
- Uses only `socket` (stdlib) - no additional dependencies
- Status is cached to avoid repeated checks

## Files to Modify

- `webstatuspi/monitor.py` - Add `check_internet_connectivity()` and integrate detection logic
- `webstatuspi/api.py` (optional) - Add `internet_status` field to JSON response when relevant

## Dependencies

- #003 Monitor loop with threading (needs monitor implementation to integrate)

## Progress Log
(No progress yet)

## Learnings
(None yet)
