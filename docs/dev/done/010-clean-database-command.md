# Task #010: Create Command to Clean the Database

## Metadata
- **Status**: completed
- **Priority**: P1 - Active
- **Slice**: Core
- **Created**: 2026-01-17
- **Started**: 2026-01-18
- **Completed**: 2026-01-18
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user, I want to manually clean old check records from the database to free up space on the SD card.

**Acceptance Criteria**:
- [x] Add `clean` subcommand to CLI
- [x] Command reads database path from config file
- [x] Command uses `retention_days` from config by default
- [x] Command accepts optional `--retention-days` flag to override config
- [x] Command accepts optional `--all` flag to delete all check records
- [x] Command displays how many records were deleted
- [x] Command validates database exists before attempting cleanup
- [x] Command handles errors gracefully with clear messages
- [x] Command uses existing `cleanup_old_checks()` function from database module

## Implementation Notes

### Command Structure
```bash
webstatuspi clean [--config CONFIG] [--retention-days DAYS] [--all]
```

### Command Options
- `--config PATH`: Path to config file (default: `config.yaml`)
- `--retention-days DAYS`: Override retention days from config
- `--all`: Delete all check records (ignore retention_days)

### Implementation Details
1. Create `_cmd_clean()` function in `webstatuspi/__init__.py`
2. Add `clean` subparser in `main()` function
3. Load config to get database path and retention_days
4. Initialize database connection
5. Call `cleanup_old_checks()` or delete all records if `--all` is specified
6. Display results to user

### Pi 1B+ Constraints
- Must be fast (avoid blocking for long)
- Should minimize database operations
- Clear output for manual execution

### Error Cases
- Config file not found
- Database file not found
- Invalid retention_days value
- Database locked (another process using it)

## Files to Modify
- `webstatuspi/__init__.py` - Add clean command handler and subparser

## Dependencies
- Uses existing `database.cleanup_old_checks()` function
- Uses existing `config.load_config()` function

## Progress Log

- [2026-01-18 00:00] Started task
- [2026-01-18 00:15] Added `delete_all_checks()` function to database.py
- [2026-01-18 00:20] Added `_cmd_clean()` function to __init__.py
- [2026-01-18 00:25] Added clean subparser to main()
- [2026-01-18 00:30] Tested all scenarios: config errors, database errors, retention-days, --all flag
- [2026-01-18 00:35] All 143 existing tests pass
- [2026-01-18 00:40] Task completed

## Learnings

- Transferred to LEARNINGS.md as L017
