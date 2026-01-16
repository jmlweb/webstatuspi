# Task #002: Database Layer (SQLite)

## Metadata
- **Status**: completed
- **Priority**: P2 - Active
- **Slice**: Core
- **Created**: 2026-01-16
- **Started**: 2026-01-17
- **Completed**: 2026-01-17
- **Blocked by**: None

## Vertical Slice Definition

**User Story**: As a system, I want to persist URL check results in SQLite for historical data and API queries.

**Acceptance Criteria**:
- [x] Define SQLite schema for status checks
- [x] Initialize database and create tables on first run
- [x] Insert new check results
- [x] Query latest status for each URL
- [x] Query status history with time range
- [x] Handle database errors gracefully
- [x] Support database path from config

## Implementation Notes

### Schema Design
```sql
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_name TEXT NOT NULL,
    url TEXT NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    is_up BOOLEAN NOT NULL,
    error_message TEXT,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_checks_url_name ON checks(url_name);
CREATE INDEX IF NOT EXISTS idx_checks_checked_at ON checks(checked_at);
```

### API Functions Needed
```python
def init_db(db_path: str) -> None
def insert_check(conn, result: CheckResult) -> None
def get_latest_status(conn) -> List[UrlStatus]
def get_history(conn, url_name: str, since: datetime) -> List[CheckResult]
def cleanup_old_checks(conn, retention_days: int) -> int  # returns count of deleted records
```

### Pi 1B+ Constraints
- Use connection pooling or single connection (low memory)
- Consider WAL mode for concurrent reads
- Auto-cleanup old records (configurable retention_days, default: 7 days)
- Cleanup runs periodically (after each check cycle) to prevent database growth
- With 5-10 URLs and 30-60s intervals: ~1.4 MB/day → 7 days ≈ 10 MB (manageable)

## Files to Modify
- `webstatuspi/database.py` (created) - Database operations
- `webstatuspi/models.py` (created) - CheckResult, UrlStatus dataclasses
- `tests/test_database.py` (created) - Unit tests (25 tests)

## Dependencies
- #001 Config loader (for database path)

## Progress Log
- [2026-01-17] Started task - Planning database layer implementation
- [2026-01-17] Created models.py with CheckResult and UrlStatus dataclasses
- [2026-01-17] Created database.py with init_db, insert_check, get_latest_status, get_history, cleanup_old_checks, get_url_names
- [2026-01-17] Added 25 unit tests covering all database operations - all passing
- [2026-01-17] Task completed

## Learnings
- L003: Source files are in `webstatuspi/` directory, not `src/` (transferred)
- L004: WAL mode enabled for better concurrent read performance on Pi (transferred)
- L005: Added composite index on (url_name, checked_at) for efficient history queries (transferred)
