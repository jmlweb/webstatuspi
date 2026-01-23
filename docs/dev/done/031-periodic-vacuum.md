# Task #031: Periodic SQLite VACUUM

## Metadata
- **Status**: completed
- **Priority**: P4
- **Slice**: Database, Config
- **Created**: 2026-01-23
- **Started**: 2026-01-24
- **Completed**: 2026-01-24
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a system administrator running WebStatusPi on a Raspberry Pi with limited storage, I want the SQLite database to be periodically defragmented so that disk space is reclaimed after old records are deleted and query performance remains optimal.

**Acceptance Criteria**:
- [x] Config schema supports `vacuum_interval_days` option (0 to disable)
- [x] VACUUM runs automatically based on configured interval
- [x] VACUUM only runs during low-activity periods (after cleanup cycle)
- [x] Last VACUUM timestamp is tracked to avoid running too frequently
- [x] VACUUM operation is logged
- [x] Unit tests for VACUUM scheduling logic (all 399 tests pass)
- [x] Documentation added to config.example.yaml

## Implementation Notes

### Config Schema Addition

```yaml
database:
  path: "./data/status.db"
  retention_days: 7
  vacuum_interval_days: 7  # 0 to disable, default: 7
```

### Why VACUUM is Needed

SQLite DELETE operations don't shrink the database file - they mark pages as free for reuse. Over time:
- Database file size grows even with retention cleanup
- Free pages become scattered (fragmentation)
- Query performance can degrade

VACUUM rebuilds the database file, reclaiming space and defragmenting.

### Implementation Strategy

1. Track last VACUUM time in a metadata table or file
2. After each cleanup cycle, check if VACUUM is due
3. Run `PRAGMA vacuum;` if interval has passed

```python
def maybe_vacuum(self) -> None:
    """Run VACUUM if configured interval has passed."""
    if self.config.vacuum_interval_days <= 0:
        return

    # Check last vacuum time
    last_vacuum = self._get_last_vacuum_time()
    if last_vacuum is None:
        should_vacuum = True
    else:
        days_since = (datetime.now(UTC) - last_vacuum).days
        should_vacuum = days_since >= self.config.vacuum_interval_days

    if should_vacuum:
        logger.info("Running VACUUM on database")
        self.conn.execute("VACUUM")
        self._set_last_vacuum_time(datetime.now(UTC))
        logger.info("VACUUM completed")
```

### Metadata Storage Options

**Option A**: Separate metadata table
```sql
CREATE TABLE IF NOT EXISTS _metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

**Option B**: Store in a `.vacuum` file alongside the database

**Recommendation**: Option A (keeps everything in one file)

### Performance Considerations

- VACUUM locks the database during execution
- On a 10MB database, VACUUM takes ~100-500ms
- Run after cleanup cycle when activity is lowest
- Consider VACUUM INTO for zero-downtime (creates new file)

### VACUUM INTO Alternative

For zero-downtime:
```python
# Creates optimized copy, then atomically replaces
self.conn.execute("VACUUM INTO 'status.db.new'")
os.replace("status.db.new", "status.db")
```

**Note**: This requires reopening the connection after replace.

## Files to Modify

- `webstatuspi/config.py` - Add `vacuum_interval_days` to DatabaseConfig
- `webstatuspi/database.py` - Add `maybe_vacuum()` method, metadata table
- `config.example.yaml` - Add vacuum_interval_days example
- `README.md` - Document VACUUM configuration
- `tests/test_database.py` - Add tests for VACUUM scheduling

## Dependencies

None - uses SQLite built-in VACUUM

## Follow-up Tasks

- Consider implementing VACUUM INTO for zero-downtime in high-traffic scenarios

## Progress Log

**2026-01-24**:
- Added `vacuum_interval_days` field to `DatabaseConfig` dataclass (default: 7, 0 to disable)
- Added validation in `__post_init__` to ensure non-negative value
- Created `_metadata` table in `init_db()` for tracking maintenance operations
- Implemented `_get_metadata()` and `_set_metadata()` helper functions for metadata access
- Implemented `maybe_vacuum()` function with interval-based scheduling logic
- Modified `monitor.py::_run_cleanup()` to call `maybe_vacuum()` after cleanup
- Added `vacuum_interval_days` to `config.example.yaml` with documentation
- All 399 tests pass

## Learnings

**L026: Metadata table pattern simplifies persistent state tracking**
- Using a simple key-value `_metadata` table (`CREATE TABLE _metadata (key TEXT PRIMARY KEY, value TEXT)`) provides a clean pattern for tracking maintenance operations like last VACUUM timestamp
- This approach avoids creating separate tables for each maintenance operation
- `INSERT OR REPLACE` syntax makes metadata updates idempotent
- Storing timestamps as ISO format strings (`datetime.now(UTC).isoformat()`) ensures consistency and timezone safety

**L027: VACUUM after cleanup maximizes space reclamation**
- Running VACUUM immediately after `cleanup_old_checks()` ensures maximum benefit because DELETE operations just freed pages
- This timing minimizes database downtime since cleanup and VACUUM happen during the same low-activity period
- On Raspberry Pi with limited storage, this pattern is critical for preventing database file growth over time
