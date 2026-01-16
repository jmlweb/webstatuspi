---
argument-hint: [task description]
description: Groom and add a new task to the backlog
model: sonnet
---

# Add Task Skill

Interactively groom a new task and add it to the development backlog.

## Usage

- `/add-task` - Interactive mode (asks questions to define task)
- `/add-task "implement buzzer alerts"` - Start with description

## Workflow

### 1. Read Current State

First, read `docs/dev/INDEX.md` to understand:
- Current task count
- Existing priorities
- Next available task number

```bash
# Get next task number
ls docs/dev/backlog/ docs/dev/done/ 2>/dev/null | grep -E '^[0-9]+' | sort -n | tail -1
```

### 2. Gather Task Information

Ask the user for:

1. **Task Name** (if not provided as argument)
   - Short, descriptive title
   - Example: "OLED display driver", "Button interrupt handling"

2. **User Story**
   - Format: "As a [role], I want [goal] so that [benefit]"
   - Help user formulate if unclear

3. **Acceptance Criteria**
   - Ask iteratively: "What else needs to be true for this to be complete?"
   - Aim for 3-6 specific, testable criteria
   - Each should be a checkbox item

4. **Slice** (suggest based on description)
   - Hardware, Core, API, Config, Display, etc.
   - Derive from files likely to be modified

5. **Dependencies**
   - "Does this task depend on any existing tasks?"
   - Show list of pending tasks for reference

### 3. Suggest Priority

Analyze and suggest priority:

| Priority | Criteria |
|----------|----------|
| P2 - Next | No blockers, small scope, unblocks others |
| P3 | Normal backlog item |
| P4 | Nice-to-have, future consideration |

**Note**: P1 is reserved for the single active task (user decides when to promote)

### 4. Generate Task File

Create `docs/dev/backlog/XXX-task-name.md`:

```markdown
# Task #XXX: Task Title

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: [detected slice]
- **Created**: [today's date]
- **Started**: -
- **Blocked by**: [dependencies or "-"]

## Vertical Slice Definition

**User Story**: [user story from step 2]

**Acceptance Criteria**:
- [ ] [criterion 1]
- [ ] [criterion 2]
- [ ] [criterion 3]

## Implementation Notes
<!-- Brief context the agent needs -->
[Add relevant notes based on discussion]

## Files to Modify
- [Suggest based on slice and description]

## Dependencies
[List task dependencies]

## Progress Log
(No progress yet)

## Learnings
(None yet)
```

### 5. Update INDEX.md

Add the new task to the backlog table in `docs/dev/INDEX.md`:
- Increment "Pending" count in Quick Stats
- Add row to Backlog table in priority order

### 6. Confirm

Show summary:
```
✓ Created task #XXX: [title]
  Priority: P3
  Slice: [slice]
  File: docs/dev/backlog/XXX-task-name.md

Next steps:
- Use /start-task XXX to begin work
- Use /dev-status to see updated backlog
```

## Task Naming Convention

File names should be:
- Lowercase
- Hyphen-separated
- Descriptive but concise
- Pattern: `XXX-short-description.md`

Examples:
- `006-buzzer-alerts.md`
- `007-config-validation.md`
- `008-systemd-service.md`

## Slice Reference

| Slice | Description | Typical Files |
|-------|-------------|---------------|
| Config | Configuration loading/validation | `src/config.py` |
| Core | Main logic, orchestration | `src/main.py`, `src/monitor.py` |
| Database | SQLite operations | `src/database.py` |
| API | HTTP endpoints | `src/api.py` |
| Hardware | Pi-specific hardware | `src/display.py`, `src/buzzer.py` |
| Display | OLED/LCD output | `src/display.py` |

## Error Handling

- If backlog directory doesn't exist: Create it
- If task number conflicts: Use next available
- If user cancels: Abort without changes
