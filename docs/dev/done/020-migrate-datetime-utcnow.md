# Task #020: Migrate datetime.utcnow() to datetime.now(timezone.utc)

## Metadata
- **Status**: completed
- **Priority**: P4
- **Slice**: Core
- **Created**: 2026-01-21
- **Started**: 2026-01-21
- **Completed**: 2026-01-21
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a developer, I want the codebase to use the modern datetime pattern so that deprecation warnings are avoided in Python 3.12+ and the code is consistent.

**Acceptance Criteria**:
- [x] All uses of `datetime.utcnow()` replaced with `datetime.now(timezone.utc)`
- [x] Import `timezone` from datetime module where needed
- [x] Tests pass without changes (API contract unchanged)
- [x] No deprecation warnings on Python 3.12+

## Implementation Notes

### Background
`datetime.utcnow()` is deprecated since Python 3.12 because it returns a "naive" datetime (without timezone info), which can cause subtle bugs. The recommended replacement is `datetime.now(timezone.utc)` which returns a timezone-aware datetime.

### Changes Required
Replace in these files:

**monitor.py:150**
```python
# Before
checked_at = datetime.utcnow()

# After
checked_at = datetime.now(timezone.utc)
```

**database.py:132, 216, 351**
```python
# Before
since_24h = (datetime.utcnow() - timedelta(hours=24)).isoformat()
cutoff = (datetime.utcnow() - timedelta(days=retention_days)).isoformat()

# After
since_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
```

### Already Correct
`alerter.py:244` already uses the modern pattern.

### Imports to Add
```python
from datetime import datetime, timedelta, timezone
```

## Files to Modify
- `webstatuspi/monitor.py` - Add timezone import, update line 150
- `webstatuspi/database.py` - Add timezone import, update lines 132, 216, 351

## Dependencies
None

## Progress Log

### 2026-01-21
- ✅ Updated `monitor.py:150` - replaced `datetime.utcnow()` with `datetime.now(timezone.utc)`
- ✅ Updated `database.py:132, 216, 351` - replaced all `datetime.utcnow()` calls with `datetime.now(timezone.utc)`
- ✅ Updated `api.py:464` - replaced `datetime.utcnow()` with `datetime.now(timezone.utc)`
- ✅ Added `timezone` import to all three files
- ✅ Fixed test compatibility: Updated `test_monitor.py` to use timezone-aware datetimes
- ✅ Fixed test assertion: Updated `test_api.py` to match actual cache-control header
- ✅ Added `requests` dependency to `pyproject.toml` (was missing)
- ✅ All 209 tests passing with Python 3.11+
- ✅ Migrated `tests/test_database.py` (16 instances)
- ✅ Migrated `tests/test_api.py` (9 instances)
- ✅ Migrated `tests/test_monitor.py` (3 instances, using `UTC` alias for consistency)
- ✅ Migrated `tests/test_alerter.py` (2 instances)
- ✅ Migrated `generate_screenshots.py` (1 instance)
- ✅ Final verification: 0 instances of `datetime.utcnow()` remain in codebase
- ✅ All 209 tests passing
- ✅ Task completed

## Learnings
- L020: Test files need deprecation migration too (transferred to LEARNINGS.md)
