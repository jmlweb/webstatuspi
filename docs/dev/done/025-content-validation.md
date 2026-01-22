# Task #025: Content Validation (Keyword/JSON)

## Metadata
- **Status**: completed
- **Priority**: P2 - Next
- **Slice**: Core, Config, Database
- **Created**: 2026-01-22
- **Started**: 2026-01-22
- **Completed**: 2026-01-22
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a developer, I want to validate that HTTP responses contain specific keywords or JSON paths so that I can monitor API health beyond just HTTP status codes and detect when services return error pages with 200 status codes.

**Acceptance Criteria**:
- [x] Config schema supports optional `keyword` or `json_path` validation
- [x] Keyword validation checks if response body contains the specified string
- [x] JSON path validation checks if JSON response matches expected value at path
- [x] Validation failures are treated as check failures (is_up = false)
- [x] Validation errors stored in error_message field
- [x] Response body reading is memory-efficient (limit size for Pi 1B+)
- [x] Unit tests for keyword and JSON path validation
- [x] Documentation added to README.md with examples

## Implementation Notes

### Config Schema Addition

```yaml
urls:
  - name: "API_PROD"
    url: "https://api.example.com/health"
    timeout: 10
    keyword: "OK"  # Optional: check if response contains this string
    
  - name: "API_STAGING"
    url: "https://staging.example.com/api/status"
    timeout: 10
    json_path: "status.healthy"  # Optional: check JSON path equals true
```

### Validation Logic

1. **Keyword Validation**:
   - Read response body (limit to 1MB for Pi 1B+ memory constraints)
   - Check if keyword string is present (case-sensitive or case-insensitive option)
   - If not found, mark check as failed

2. **JSON Path Validation**:
   - Parse response as JSON
   - Navigate path (e.g., "status.healthy" → `response["status"]["healthy"]`)
   - Check if value matches expected (boolean true, string "ok", etc.)
   - If path missing or value mismatch, mark check as failed

### Memory Constraints (Pi 1B+)

- Limit response body reading to 1MB max
- Use streaming/chunked reading if possible
- Don't store full body in database (only validation result)

### Database Changes

- No schema changes needed
- Use existing `error_message` field for validation failures
- `is_up` field already handles success/failure

### Performance Impact

- Minimal: only reads response body when validation configured
- Keyword check: O(n) string search
- JSON parsing: lightweight for small responses
- No impact on URLs without validation

## Files to Modify

**Modified Files**:
- `webstatuspi/config.py` - Add optional `keyword` and `json_path` to UrlConfig
- `webstatuspi/monitor.py` - Add validation logic after HTTP response
- `config.example.yaml` - Add validation examples
- `README.md` - Document content validation feature
- `tests/test_monitor.py` - Add tests for keyword and JSON validation

## Dependencies

None - uses stdlib `json` module

## Follow-up Tasks

None

## Progress Log

**2026-01-22**: Implementation completed
- Added `keyword` and `json_path` optional fields to `UrlConfig` dataclass
- Implemented `_validate_keyword()` helper function for case-sensitive substring matching
- Implemented `_validate_json_path()` helper function with dot-notation support
- Integrated validation logic into `check_url()` function with 1MB body size limit
- Added 12 comprehensive unit tests covering success/failure cases for both validation types
- Updated `config.example.yaml` with validation examples
- Added "Content Validation" section to README.md with use cases and examples
- All tests passing (293 tests total, 12 new for content validation)
- Code style validated with ruff check and format

## Learnings

### L023: Response body reading must limit size for memory efficiency
**Date**: 2026-01-22
**Task**: #025 Content Validation
**Context**: Implementing content validation on Pi 1B+ with 512MB RAM
**Learning**: When reading response bodies for validation, always limit the size to prevent memory exhaustion on constrained devices. Using `response.read(MAX_BODY_SIZE)` with a 1MB limit ensures that even if a service returns a large HTML error page or dumps logs, the monitoring system won't crash. The `read(n)` method only reads up to n bytes, making it safe and efficient.
**Action**: Added `MAX_BODY_SIZE = 1024 * 1024` constant and used `response.read(MAX_BODY_SIZE)` in validation logic.

### L024: Validation should only run on successful HTTP responses
**Date**: 2026-01-22
**Task**: #025 Content Validation
**Context**: Implementing content validation for keyword and JSON path checking
**Learning**: Content validation should only execute when the initial HTTP check succeeds (2xx/3xx status codes). If the HTTP request fails (4xx, 5xx, timeout, connection error), attempting to read and validate the response body is wasteful and can complicate error reporting. By checking `is_up` before validation, we ensure validation only runs when it's meaningful and avoid masking the actual HTTP error with a validation error.
**Action**: Wrapped validation logic with `if is_up and (url_config.keyword or url_config.json_path):` condition.

### L025: JSON path validation benefits from truthy value checking
**Date**: 2026-01-22
**Task**: #025 Content Validation
**Context**: Implementing JSON path validation for health check endpoints
**Learning**: Health check APIs often use different conventions for success indicators: boolean `true`, strings like `"ok"` or `"healthy"`, or numeric `1`. Rather than requiring exact value matching (which would need additional config complexity), checking if the final value is truthy covers all these cases naturally and provides a simpler, more flexible API. This follows Python's truthiness semantics and handles most real-world health check patterns.
**Action**: Implemented truthy check with `if not current:` to accept any truthy value (true, "ok", 1, etc.) and reject falsy values (false, null, 0, empty string).
