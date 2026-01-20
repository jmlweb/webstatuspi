# Task #013: Locale-aware date/time formatting

## Metadata
- **Status**: completed
- **Priority**: P1 - Active
- **Slice**: API
- **Created**: 2026-01-18
- **Started**: 2026-01-20
- **Completed**: 2026-01-20
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user, I want to see dates in my local format so that timestamps are familiar and easier to read.

**Acceptance Criteria**:
- [x] Dashboard timestamps (last check times) use browser locale formatting
- [x] History modal timestamps use browser locale formatting
- [x] Date format automatically detects browser's locale settings via `navigator.language`
- [x] Time format (12h/24h) respects locale preferences
- [x] All existing functionality continues to work (no regressions)

## Implementation Notes

Currently, the dashboard uses hardcoded formats:
- `formatTime()` in `_dashboard.py:1057` uses `toLocaleTimeString('en-US', { hour12: false })`
- `formatDateTime()` in `_dashboard.py:1289` uses manual formatting with hardcoded `MM-DD HH:mm:ss`

**Approach**:
1. Replace `'en-US'` with `navigator.language` or `navigator.languages[0]`
2. Update `formatDateTime()` to use `toLocaleDateString()` and `toLocaleTimeString()`
3. Consider using `Intl.DateTimeFormat` for consistent formatting
4. Test with different locales (en-US, es-ES, ja-JP, de-DE)

## Files to Modify
- `webstatuspi/_dashboard.py` - Update JavaScript date formatting functions

## Dependencies
None

## Progress Log
- [2026-01-20 17:00] Started task - analyzing current implementation
- [2026-01-20 17:05] Updated formatTime() to use navigator.language instead of 'en-US'
- [2026-01-20 17:06] Updated formatDateTime() to use toLocaleString() with locale-aware options
- [2026-01-20 17:07] All 148 tests pass - no regressions
- [2026-01-20 17:10] Task completed - all acceptance criteria met

## Learnings
(None yet)
