# Task #027: Custom Status Code Ranges

## Metadata
- **Status**: done
- **Priority**: P3
- **Slice**: Config, Core
- **Created**: 2026-01-22
- **Started**: 2026-01-22
- **Completed**: 2026-01-22
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a developer, I want to define custom HTTP status code ranges that indicate success so that I can monitor APIs that use non-standard status codes (e.g., 201 Created, 202 Accepted) or handle specific error codes as acceptable.

**Acceptance Criteria**:
- [x] Config schema supports optional `success_codes` per URL
- [x] Default behavior unchanged (200-399 = success) if not specified
- [x] Supports single codes (e.g., `[200, 201]`) or ranges (e.g., `[200-299, 400]`)
- [x] Validation ensures valid HTTP status codes (100-599)
- [x] Unit tests for custom status code logic
- [x] Documentation added to README.md with examples

## Implementation Notes

### Config Schema Addition

```yaml
urls:
  - name: "API_CREATE"
    url: "https://api.example.com/create"
    timeout: 10
    success_codes: [200, 201, 202]  # Accept 200, 201, 202 as success
    
  - name: "API_LEGACY"
    url: "https://legacy.example.com"
    timeout: 10
    success_codes: [200-299, 400]  # Accept 2xx range and 400 (weird API)
```

### Status Code Parsing

Support two formats:
1. **Single codes**: `[200, 201, 202]`
2. **Ranges**: `[200-299, 400]` (200 to 299 inclusive, plus 400)

### Default Behavior

- If `success_codes` not specified: use default `200-399` range
- Maintains backward compatibility

### Implementation

In `monitor.py` `check_url()`:
```python
def _is_success_status(status_code: int, success_codes: list[int | str] | None) -> bool:
    if success_codes is None:
        return 200 <= status_code < 400  # Default behavior
    
    for code in success_codes:
        if isinstance(code, int):
            if status_code == code:
                return True
        elif isinstance(code, str) and '-' in code:
            # Parse range "200-299"
            start, end = map(int, code.split('-'))
            if start <= status_code <= end:
                return True
    return False
```

### Performance Impact

- Zero overhead: simple integer comparison
- No database changes needed
- No API changes needed (is_up field already handles it)

## Files to Modify

**Modified Files**:
- `webstatuspi/config.py` - Add optional `success_codes` to UrlConfig with validation
- `webstatuspi/monitor.py` - Update `is_up` logic to use custom codes
- `config.example.yaml` - Add success_codes examples
- `README.md` - Document custom status codes
- `tests/test_config.py` - Add tests for success_codes validation
- `tests/test_monitor.py` - Add tests for custom status code logic

## Dependencies

None - pure logic change

## Follow-up Tasks

None

## Progress Log

- 2026-01-22: Implemented `_parse_success_codes()` in config.py to parse single codes and ranges
- 2026-01-22: Added `success_codes` field to UrlConfig dataclass
- 2026-01-22: Implemented `_is_success_status()` in monitor.py to evaluate custom codes
- 2026-01-22: Updated `check_url()` to use custom success codes
- 2026-01-22: Added comprehensive tests for config parsing and monitor logic
- 2026-01-22: Updated config.example.yaml with success_codes examples
- 2026-01-22: Added documentation to README.md

## Learnings

- Ranges stored as tuples internally for efficient evaluation
- Config validation at parse time prevents runtime errors
