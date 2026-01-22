# Task #025: Content Validation (Keyword/JSON)

## Metadata
- **Status**: pending
- **Priority**: P2 - Next
- **Slice**: Core, Config, Database
- **Created**: 2026-01-22
- **Started**: -
- **Completed**: -
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a developer, I want to validate that HTTP responses contain specific keywords or JSON paths so that I can monitor API health beyond just HTTP status codes and detect when services return error pages with 200 status codes.

**Acceptance Criteria**:
- [ ] Config schema supports optional `keyword` or `json_path` validation
- [ ] Keyword validation checks if response body contains the specified string
- [ ] JSON path validation checks if JSON response matches expected value at path
- [ ] Validation failures are treated as check failures (is_up = false)
- [ ] Validation errors stored in error_message field
- [ ] Response body reading is memory-efficient (limit size for Pi 1B+)
- [ ] Unit tests for keyword and JSON path validation
- [ ] Documentation added to README.md with examples

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

(To be filled during implementation)

## Learnings

(To be filled during implementation)
