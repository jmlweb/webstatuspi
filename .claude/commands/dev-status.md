---
argument-hint:
description: Show current development status from INDEX.md
model: haiku
---

# Dev Status Skill

Display current development status, active task, and backlog overview.

## Usage

- `/dev-status` - Show full status
- `/dev-status summary` - Show only quick stats

## Workflow

### 1. Read INDEX.md

Read `docs/dev/INDEX.md` and parse:
- Quick Stats section
- Current Focus section
- Backlog table

### 2. Display Status

```
## WebStatusπ Development Status

### Quick Stats
┌──────────────┬───────┐
│ Pending      │   5   │
│ In Progress  │   1   │
│ Completed    │   3   │
│ Blocked      │   0   │
└──────────────┴───────┘

### Current Focus
► Task #004: OLED display driver
  Status: in_progress
  Slice: Hardware
  Started: 2026-01-16

### Backlog (by priority)
| # | Task | Slice | Priority |
|---|------|-------|----------|
| 004 | OLED display driver | Hardware | P1 - Active |
| 005 | Button handling | Hardware | P2 - Next |
| 006 | Buzzer alerts | Hardware | P3 |
| 007 | Config validation | Config | P3 |
| 008 | Systemd service | Core | P4 |

### Recent Activity
- [2026-01-16] Started #004
- [2026-01-15] Completed #003
- [2026-01-15] Completed #002

### Quick Actions
- /start-task 005  → Start next task
- /check-task      → Verify active task
- /add-task        → Add new task
```

### 3. Summary Mode

If `/dev-status summary`:

```
## Dev Status Summary
Pending: 5 | Active: #004 OLED display | Done: 3
Next up: #005 Button handling (P2)
```

## Additional Checks

### Blocked Tasks Warning

If blocked tasks exist:
```
⚠️ Blocked Tasks
- #003: Waiting for hardware delivery
- #006: Depends on #005
```

### Stale Tasks Warning

If a task has been in_progress for >3 days:
```
⚠️ Stale Task
Task #004 has been in_progress since 2026-01-12 (4 days)
Consider: /check-task 004 or /block-task 004
```

### Priority Imbalance

If too many P2 tasks:
```
ℹ️ Priority Note
You have 4 tasks marked as P2 - Next
Consider promoting one to P1 - Active
```

## Health Indicators

```
## Project Health

✓ INDEX.md exists and is valid
✓ LEARNINGS.md exists
✓ 5 tasks in backlog
✓ 3 tasks completed
⚠️ 0 learnings documented (consider adding learnings)
```

## Files Checked

- `docs/dev/INDEX.md` - Main status
- `docs/dev/LEARNINGS.md` - Learning count
- `docs/dev/backlog/*.md` - Pending task count
- `docs/dev/done/*.md` - Completed task count

## Error Handling

- INDEX.md missing: "Run /add-task to initialize task system"
- Backlog empty: "No pending tasks. Use /add-task to create one"
- Parse error: Show raw INDEX.md content
