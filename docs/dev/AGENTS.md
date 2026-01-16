# Development Workflow Rules

Rules and conventions for AI agents working on WebStatusPi tasks.

## Entry Point

1. **Read [INDEX.md](INDEX.md) first** - Shows current status and backlog
2. **Read the specific task file** from `backlog/` for the task you're working on
3. **Consult [LEARNINGS.md](LEARNINGS.md)** if relevant to the task's domain

## Task Lifecycle

### Starting a Task

1. Update task status to `in_progress` in the task file
2. Update INDEX.md "Current Focus" section
3. Read acceptance criteria in task file

### Working on a Task

1. Follow acceptance criteria in task file
2. Log progress in task's "Progress Log" section
3. **Document learnings immediately** - don't wait until completion

### Completing a Task

1. Mark all checkboxes in task file
2. Change status to `completed`
3. Move file: `backlog/XXX.md` → `done/XXX.md`
4. Update INDEX.md (stats + backlog table)
5. Move any learnings to LEARNINGS.md

### Blocking a Task

If you cannot proceed:
1. Change status to `blocked`
2. Document the blocker in the task file
3. Update INDEX.md to reflect blocked status

## Commands Reference

| Command | Description |
|---------|-------------|
| `task:start #XXX` | Mark task as in_progress, update INDEX |
| `task:complete #XXX` | Move to done/, update INDEX |
| `task:block #XXX [reason]` | Mark blocked, document reason |
| `learning:add [content]` | Add to LEARNINGS.md |
| `status:update` | Recalculate stats in INDEX.md |

## Priority Levels

| Priority | Meaning | Max Count |
|----------|---------|-----------|
| **P1 - Active** | Currently being worked on | 1 |
| **P2 - Next** | Next in queue | 2 |
| **P3** | Normal backlog | Unlimited |
| **P4** | Nice-to-have / Future | Unlimited |

## Critical: Document Learnings Immediately

**Call `/add-learning` immediately when:**
- Discovering unexpected behavior
- Finding a solution to a problem
- Encountering Pi 1B+ specific constraints
- Learning project-specific patterns

**DO NOT wait until task completion.** Document learnings as you discover them.

**DO NOT add learnings for:**
- Expected behavior ("X works as documented")
- Routine implementation ("added function Y")
- General knowledge about standard libraries

## Directory Structure

```
docs/dev/
├── INDEX.md        # Current status (dynamic)
├── AGENTS.md       # This file - workflow rules (static)
├── LEARNINGS.md    # Knowledge base
├── backlog/        # Pending tasks
│   └── XXX-task-name.md
└── done/           # Completed tasks
    └── XXX-task-name.md
```
