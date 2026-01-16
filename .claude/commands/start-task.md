---
argument-hint: [task number]
description: Mark a task as in-progress and set as current focus
model: haiku
---

# Start Task Skill

Mark a task as in-progress, update INDEX.md, and prepare for work.

## Usage

- `/start-task 003` - Start task #003
- `/start-task` - Show pending tasks and ask which to start

## Workflow

### 1. Validate

If task number provided:
- Check `docs/dev/backlog/XXX-*.md` exists
- Verify status is `pending` (not already in_progress or blocked)

If no task number:
- Read `docs/dev/INDEX.md`
- Show pending tasks with priorities
- Ask user which to start

### 2. Check for Active Task

Read `docs/dev/INDEX.md` Current Focus section:
- If another task is in_progress, warn user
- Ask: "Task #YYY is currently active. Switch to #XXX?"
- Only one task can be in_progress at a time

### 3. Update Task File

In `docs/dev/backlog/XXX-*.md`:

```markdown
## Metadata
- **Status**: in_progress  # Changed from pending
- **Priority**: P1 - Active  # Promoted to P1
- **Started**: [today's date]  # Set start date
```

Add to Progress Log:
```markdown
## Progress Log
- [YYYY-MM-DD HH:MM] Started task
```

### 4. Update INDEX.md

1. **Quick Stats**: Adjust counts
   - Decrement "Pending"
   - Increment "In Progress" to 1

2. **Current Focus**: Update quote block
   ```markdown
   ## Current Focus
   > Task #XXX: [task title]
   ```

3. **Backlog Table**: Update priority
   ```markdown
   | XXX | [title] | [slice] | P1 - Active |
   ```

### 5. Show Task Summary

Display for the agent/user:
```
✓ Started task #XXX: [title]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Files to Modify
- src/file1.py
- src/file2.py

## Implementation Notes
[relevant notes from task file]

Ready to work. Remember:
- Update progress in task file as you work
- Use /add-learning when you discover something important
- Use /complete-task when all criteria are met
```

## Validation Rules

1. **Task must exist** in `docs/dev/backlog/`
2. **Task must be pending** (not blocked or already active)
3. **Only one active task** at a time
4. **Blocked tasks cannot start** - show blocker info

## If Task is Blocked

```
❌ Cannot start task #XXX

This task is blocked by: #YYY

Options:
1. Start blocker task #YYY first
2. Remove the block (edit task file)
3. Choose a different task
```

## Error Handling

- Task not found: List available tasks
- Already in_progress: Show current status, ask to switch
- Blocked: Show blocker, suggest alternatives
