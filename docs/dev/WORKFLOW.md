# Development Workflow Rules

Rules and conventions for AI agents working on WebStatusPi tasks.

## Entry Point

1. **Read [INDEX.md](INDEX.md) first** - Shows current status and backlog
2. **Read [LEARNINGS.md](LEARNINGS.md)** - **REQUIRED** before any implementation. Contains critical lessons about Pi 1B+ constraints, project patterns, and solutions to problems. Ignoring this file may lead to repeating past mistakes.
3. **Read the specific task file** from `backlog/` for the task you're working on

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

> **Note**: These commands are defined as skills in `.claude/commands/` and are invoked
> with `/command-name` during a Claude Code session.

| Command | Description |
|---------|-------------|
| `/start-task XXX` | Mark task as in_progress, update INDEX |
| `/complete-task XXX` | Move to done/, update INDEX |
| `/block-task XXX [reason]` | Mark blocked, document reason |
| `/add-learning` | Add to LEARNINGS.md |
| `/dev-status` | Show current status from INDEX.md |
| `/check-task XXX` | Verify task status matches reality |
| `/next-task` | Suggest next priority task |
| `/add-task` | Groom and add a new task to the backlog |
| `/sync-docs` | Verify documentation matches implementation |
| `/test` | Run tests with coverage report |
| `/lint` | Run linters (flake8, mypy) on Python code |
| `/deploy` | Deploy to Raspberry Pi via git pull |

## Slices (System Areas)

Tasks are categorized by slice to indicate which parts of the system they affect:

| Slice | Description | Key Files |
|-------|-------------|-----------|
| **Core** | Main monitoring logic | `monitor.py`, `checker.py` |
| **Config** | Configuration and validation | `config.py`, `config.yaml` |
| **Database** | Persistence layer | `database.py`, `models.py` |
| **API** | HTTP server and endpoints | `api.py`, `_dashboard.py` |
| **Alerts** | Alert system | `alerter.py`, webhooks |
| **Frontend** | Dashboard HTML/CSS/JS | `_dashboard.py`, static assets |
| **Testing** | Unit and integration tests | `tests/` |
| **DevOps** | CI/CD, deployment, systemd | `.github/`, `systemd/` |
| **Docs** | Documentation | `docs/`, `README.md` |

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
├── WORKFLOW.md     # This file - workflow rules (static)
├── LEARNINGS.md    # Knowledge base
├── backlog/        # Pending tasks
│   └── XXX-task-name.md
└── done/           # Completed tasks
    └── XXX-task-name.md
```
