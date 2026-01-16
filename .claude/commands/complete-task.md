---
argument-hint: [task number]
description: Complete a task, move to done, update INDEX
model: sonnet
---

# Complete Task Skill

Mark a task as completed, move to done/, transfer learnings, and update INDEX.

## Usage

- `/complete-task` - Complete current active task
- `/complete-task 003` - Complete specific task #003

## Workflow

### 1. Identify Task

If no argument:
- Read `docs/dev/INDEX.md` Current Focus
- Use the active task

If argument provided:
- Validate task exists in `docs/dev/backlog/`

### 2. Verify Completion

Read the task file and check:

1. **All acceptance criteria checked?**
   ```markdown
   - [x] Criterion 1  ✓
   - [x] Criterion 2  ✓
   - [ ] Criterion 3  ❌ NOT CHECKED
   ```

2. **If incomplete criteria exist:**
   ```
   ⚠️ Task #XXX has unchecked acceptance criteria:

   - [ ] Criterion 3
   - [ ] Criterion 4

   Options:
   1. Mark as complete anyway (criteria no longer relevant)
   2. Continue working (abort completion)
   3. Update criteria (remove/modify items)
   ```

### 3. Extract Learnings

Check task file for learnings section:

```markdown
## Learnings
- L001: Something important discovered
- L002: Another insight
```

If learnings exist:
1. Read `docs/dev/LEARNINGS.md`
2. Determine next learning ID (LXXX)
3. Format each learning properly
4. Append to appropriate category section
5. Clear learnings from task file (or mark as transferred)

### 4. Update Task File

```markdown
## Metadata
- **Status**: completed  # Changed
- **Completed**: [today's date]  # Added
```

Add final entry to Progress Log:
```markdown
## Progress Log
- [YYYY-MM-DD HH:MM] Started task
- [YYYY-MM-DD HH:MM] [other entries...]
- [YYYY-MM-DD HH:MM] Task completed
```

### 5. Move Task File

```bash
mv docs/dev/backlog/XXX-task-name.md docs/dev/done/XXX-task-name.md
```

### 6. Update INDEX.md

1. **Quick Stats**:
   ```markdown
   - **Pending**: N tasks  # Unchanged or -1 if was pending
   - **In Progress**: 0 tasks  # Now 0
   - **Completed**: M+1 tasks  # Increment
   ```

2. **Current Focus**:
   ```markdown
   ## Current Focus
   > No active task. Next up: Task #YYY
   ```

3. **Backlog Table**: Remove completed task row

### 7. Suggest Next Task

Read remaining backlog and suggest:

```
✓ Completed task #XXX: [title]

Learnings transferred: 2 items added to LEARNINGS.md

## Next Tasks (by priority)
| # | Task | Priority |
|---|------|----------|
| 004 | Next task | P2 - Next |
| 005 | Another task | P3 |

Use /start-task 004 to begin next task
```

## Learning Transfer Format

When moving learnings to LEARNINGS.md:

```markdown
### LXXX: Brief title
**Date**: YYYY-MM-DD
**Task**: #XXX Task title
**Context**: What was being attempted
**Learning**: What was discovered
**Action**: How it was applied/documented
```

## Validation Rules

1. **Task must exist** in backlog
2. **Recommend all criteria checked** (warn if not)
3. **Transfer learnings** before moving file
4. **Update all references** in INDEX.md

## Post-Completion Checks

After completing:
1. Verify file moved to `docs/dev/done/`
2. Verify INDEX.md stats are correct
3. Verify LEARNINGS.md updated (if applicable)
4. Show remaining task count

## Error Handling

- Task not found: List active/pending tasks
- No active task and no argument: Show pending tasks
- File move fails: Report error, suggest manual fix
