# Task #002: Database Layer (SQLite)

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: Core
- **Created**: 2026-01-16
- **Started**: -
- **Blocked by**: #001 (needs config for db path)

## Vertical Slice Definition

**User Story**: As a system, I want to persist URL check results in SQLite for historical data and API queries.

**Acceptance Criteria**:
- [ ] Define SQLite schema for status checks
- [ ] Initialize database and create tables on first run
- [ ] Insert new check results
- [ ] Query latest status for each URL
- [ ] Query status history with time range
- [ ] Handle database errors gracefully
- [ ] Support database path from config

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
- `src/database.py` (create) - Database operations
- `src/models.py` (create) - CheckResult, UrlStatus dataclasses

## Dependencies
- #001 Config loader (for database path)

## Progress Log
(No progress yet)

## Learnings
(None yet)
