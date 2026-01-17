# Task #010: Create Command to Clean the Database

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: Core
- **Created**: 2026-01-17
- **Started**: -
- **Completed**: -
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user, I want to manually clean old check records from the database to free up space on the SD card.

**Acceptance Criteria**:
- [ ] Add `clean` subcommand to CLI
- [ ] Command reads database path from config file
- [ ] Command uses `retention_days` from config by default
- [ ] Command accepts optional `--retention-days` flag to override config
- [ ] Command accepts optional `--all` flag to delete all check records
- [ ] Command displays how many records were deleted
- [ ] Command validates database exists before attempting cleanup
- [ ] Command handles errors gracefully with clear messages
- [ ] Command uses existing `cleanup_old_checks()` function from database module

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

(To be filled during implementation)

## Learnings

(To be filled during implementation)
