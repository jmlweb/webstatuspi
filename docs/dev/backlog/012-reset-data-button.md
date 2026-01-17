# Task #012: Reset Data Button with Confirmation Modal

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: API
- **Created**: 2026-01-18
- **Started**: -
- **Completed**: -
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user, I want to reset all monitoring data from the dashboard with a confirmation modal, so that I can clear historical statistics without using the command line.

**Acceptance Criteria**:
- [ ] Add "Reset Data" button in the dashboard header or summary bar
- [ ] Button follows cyberpunk design theme (matches existing dashboard styles)
- [ ] Clicking button shows confirmation modal (reuse existing modal system)
- [ ] Confirmation modal displays warning message about data deletion
- [ ] Modal has "Cancel" and "Confirm" buttons
- [ ] Confirmation triggers DELETE request to `/reset` API endpoint
- [ ] API endpoint `/reset` deletes all check records from database
- [ ] API endpoint returns success/error JSON response
- [ ] Dashboard refreshes after successful reset
- [ ] Error handling displays user-friendly messages on failure
- [ ] Button is visually distinct but non-intrusive

## Implementation Notes

### Dashboard Changes

1. **Reset Button Location**: Add to summary bar (next to updated time) or header
2. **Button Styling**: 
   - Use cyberpunk theme colors (`--red` or `--orange` for danger)
   - Small, subtle design to match existing UI
   - Hover effects consistent with other interactive elements

3. **Confirmation Modal**:
   - Reuse existing modal system (`.modal`, `.modal-content`)
   - Warning message: "This will delete all monitoring data. This action cannot be undone."
   - Two buttons: Cancel (close modal) and Confirm (proceed with reset)
   - Confirm button uses danger color (`--red`)

4. **JavaScript Implementation**:
   - `showResetModal()` - Display confirmation modal
   - `confirmReset()` - Handle confirmation, send DELETE request
   - `cancelReset()` - Close modal
   - Handle response and refresh dashboard data

### API Changes

1. **New Endpoint**: `DELETE /reset`
   - Handler: `_handle_reset()` in `StatusHandler`
   - Calls new database function `delete_all_checks()`
   - Returns JSON: `{"success": true, "deleted": count}` or error

2. **Database Function**: 
   - Add `delete_all_checks(conn: sqlite3.Connection) -> int` to `database.py`
   - Deletes all records from `checks` table
   - Returns count of deleted records
   - Handles errors gracefully

### Error Handling

- Database errors: Return 500 with clear message
- Network errors: Display error in dashboard
- User cancellation: Silent (just close modal)

### Pi 1B+ Constraints

- Keep modal lightweight (reuse existing CSS)
- Minimize JavaScript code (vanilla JS only)
- Fast database operation (DELETE is efficient)
- No external dependencies

## Files to Modify

- `webstatuspi/_dashboard.py` - Add reset button HTML, modal HTML, JavaScript handlers
- `webstatuspi/api.py` - Add DELETE /reset endpoint handler
- `webstatuspi/database.py` - Add `delete_all_checks()` function
- `tests/test_api.py` - Add tests for DELETE /reset endpoint
- `tests/test_database.py` - Add tests for `delete_all_checks()` function

## Dependencies

- Uses existing modal system in dashboard
- Uses existing database connection pattern
- No new external dependencies

## Progress Log

(To be filled during implementation)

## Learnings

(To be filled during implementation)
