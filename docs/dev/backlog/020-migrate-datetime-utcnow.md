# Task #020: Migrate datetime.utcnow() to datetime.now(timezone.utc)

## Metadata
- **Status**: pending
- **Priority**: P4
- **Slice**: Core
- **Created**: 2026-01-21
- **Started**: -
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a developer, I want the codebase to use the modern datetime pattern so that deprecation warnings are avoided in Python 3.12+ and the code is consistent.

**Acceptance Criteria**:
- [ ] All uses of `datetime.utcnow()` replaced with `datetime.now(timezone.utc)`
- [ ] Import `timezone` from datetime module where needed
- [ ] Tests pass without changes (API contract unchanged)
- [ ] No deprecation warnings on Python 3.12+

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
(No progress yet)

## Learnings
(None yet)
