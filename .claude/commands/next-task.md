---
argument-hint:
description: Suggest and optionally start the next priority task
model: haiku
---

# Next Task Skill

Analyze backlog and suggest the best next task to work on.

## Usage

- `/next-task` - Analyze and suggest next task
- After suggestion, prompts to start

## Workflow

### 1. Check Current State

Read `docs/dev/INDEX.md`:
- Is there an active task (in_progress)?
- What are the pending tasks?
- What are the blocked tasks?

### 2. If Active Task Exists

```
ℹ️ Active Task

You currently have task #004 in progress.

Options:
1. Continue with #004 (/check-task 004 to see status)
2. Complete #004 first (/complete-task)
3. Block #004 and switch (/block-task 004)

Proceed with current task or switch?
```

### 3. Analyze Candidates

For each pending (non-blocked) task, score based on:

| Factor | Weight | Criteria |
|--------|--------|----------|
| Priority | High | P2 > P3 > P4 |
| Dependencies | High | No blockers > has blockers |
| Unblocks others | Medium | Enables more tasks |
| Slice continuity | Low | Same slice as last completed |
| Age | Low | Older tasks slight preference |

### 4. Present Recommendation

```
## Next Task Recommendation

### Top Pick: Task #005
**Button interrupt handling** (Hardware, P2)

Why this task:
- Highest priority pending task
- No dependencies/blockers
- Unblocks: #007 (buzzer alerts)
- Same slice as recently completed work

### Alternatives

| # | Task | Priority | Notes |
|---|------|----------|-------|
| 006 | Config validation | P3 | Quick win, standalone |
| 007 | Buzzer alerts | P3 | Blocked by #005 |

### Recommendation
Start with #005 to maintain momentum on Hardware slice
and unblock dependent tasks.

Start task #005? (yes/no/other)
```

### 5. Handle Response

**If yes:**
- Execute `/start-task 005` logic
- Update task status and INDEX.md
- Show task details for starting work

**If no:**
- "OK, use /start-task XXX when ready"

**If other (number):**
- Start the specified task instead

## Selection Logic

### Priority Rules

1. **P2 tasks first** (max 2 should exist)
2. **Within same priority, prefer:**
   - Tasks that unblock others
   - Tasks with no dependencies
   - Tasks in same slice (context continuity)
   - Older tasks (prevent stagnation)

3. **Never suggest blocked tasks**

### Dependency Analysis

```python
# Pseudo-logic for dependency check
for task in pending_tasks:
    if task.blocked_by:
        blocker = find_task(task.blocked_by)
        if blocker.status != 'completed':
            task.is_blocked = True
```

### Unblocks Calculation

Check all tasks to see what completing this task would unblock:
```
Task #005 unblocks:
- #007 (buzzer alerts) - depends on #005
- #009 (input system) - depends on #005
Total: 2 tasks unblocked
```

## Edge Cases

### All Tasks Blocked

```
⚠️ All Pending Tasks Are Blocked

| Task | Blocked By |
|------|------------|
| #005 | #003 (external: hardware) |
| #006 | #005 |
| #007 | #005 |

Options:
1. Resolve blocker on #003
2. Add a new unblocked task (/add-task)
3. Review if blockers still apply (/check-task)
```

### No Pending Tasks

```
✓ All Tasks Complete!

No pending tasks in backlog.

Options:
1. Add new tasks (/add-task)
2. Review learnings (/dev-status)
3. Check for issues in completed tasks
```

### Many P2 Tasks

```
ℹ️ Multiple P2 Tasks

You have 3 tasks marked as P2 - Next:
- #005 Button handling
- #006 Config validation
- #008 Error handling

Recommend picking ONE as P1 - Active.
Which should be the priority?
```

## Integration

After `/next-task`:
- Automatically flows into `/start-task` if user confirms
- Updates INDEX.md Current Focus
- Prepares context for work

## Error Handling

- INDEX.md missing: "Initialize task system first"
- No backlog directory: Create it
- Parse errors: Show raw data for debugging
