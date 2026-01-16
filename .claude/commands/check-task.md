---
argument-hint: [task number]
description: Verify task status matches reality, fix if needed
model: sonnet
---

# Check Task Skill

Verify that a task's status accurately reflects implementation reality.

## Usage

- `/check-task 003` - Check specific task
- `/check-task` - Check current active task or all pending tasks

## Workflow

### 1. Load Task

Read the task file from `docs/dev/backlog/` or `docs/dev/done/`:
- Parse acceptance criteria
- Note current status
- Identify files to check

### 2. Verify Implementation

For each acceptance criterion, check if it's actually implemented:

1. **Read referenced files** from "Files to Modify" section
2. **Search for implementations** matching criteria
3. **Run relevant checks** if possible (imports, function existence, etc.)

### 3. Compare Status vs Reality

| File Status | Reality | Action |
|-------------|---------|--------|
| pending | Not implemented | ✓ Correct |
| pending | Fully implemented | ⚠️ Should complete |
| pending | Partially done | Update checkboxes |
| in_progress | Partially done | ✓ Correct |
| in_progress | Fully done | ⚠️ Should complete |
| completed | Still works | ✓ Correct |
| completed | Broken/missing | ⚠️ Reopen task |

### 4. Report Findings

```
## Task #XXX Status Check

Current status: pending
Location: docs/dev/backlog/003-monitor-loop.md

### Acceptance Criteria Analysis

| Criterion | File Status | Reality | Match |
|-----------|-------------|---------|-------|
| Poll each URL at interval | [ ] | Implemented in monitor.py:45 | ❌ |
| Use threading | [ ] | Implemented in monitor.py:12 | ❌ |
| Store results in database | [ ] | Not found | ✓ |
| Handle graceful shutdown | [ ] | Not found | ✓ |

### Findings
- 2 criteria are implemented but not checked
- Task appears partially complete

### Recommended Actions
1. Update task file to check completed criteria
2. Continue implementation for remaining items
3. OR: Split into smaller tasks
```

### 5. Offer Fixes

Based on findings:

**If task should be completed:**
```
Task #XXX appears fully implemented but still in backlog.

Actions:
1. Run /complete-task XXX (move to done)
2. Update checkboxes only (keep in backlog)
3. No changes (I'll verify manually)
```

**If task should be reopened:**
```
Task #XXX is marked complete but implementation is missing/broken.

Actions:
1. Move back to backlog and mark pending
2. Create new task for missing functionality
3. No changes (implementation is elsewhere)
```

**If partially complete:**
```
Task #XXX has some criteria implemented.

Actions:
1. Update checkboxes to reflect reality
2. Mark remaining work clearly
3. Continue with /start-task XXX
```

### 6. Re-evaluate Priority

If task status changed, suggest priority adjustment:

```
Task status changed from pending → should be completed.

Before: P3 (normal backlog)
Suggested: Complete and archive

OR if reopening:
Before: completed
Suggested: P2 (needs immediate attention)
```

## Deep Verification Techniques

### For Code Criteria
```python
# Check if function exists
grep -n "def function_name" src/file.py

# Check if class exists
grep -n "class ClassName" src/file.py

# Check if import exists
grep -n "from module import" src/file.py
```

### For Configuration Criteria
```bash
# Check if config key exists
grep -n "key_name:" config.yaml
```

### For File Criteria
```bash
# Check if file exists
ls -la path/to/expected/file
```

## Batch Check Mode

When called without argument, check all tasks:

```
## Backlog Health Check

Checked 5 tasks in backlog/

| Task | Status | Reality | Action Needed |
|------|--------|---------|---------------|
| #001 | pending | pending | None |
| #002 | pending | done | Complete it |
| #003 | in_progress | partial | Update checks |
| #004 | pending | pending | None |
| #005 | blocked | resolved | Unblock it |

Summary: 2 tasks need attention
```

## Integration with Other Skills

After check-task:
- Use `/complete-task` to complete found-done tasks
- Use `/start-task` to resume partial tasks
- Use `/add-learning` if discoveries were made during check

## Error Handling

- Task not found: Search in both backlog/ and done/
- Cannot verify (no files specified): Ask user for guidance
- Ambiguous results: Present findings, let user decide
