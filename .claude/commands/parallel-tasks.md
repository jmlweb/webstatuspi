---
argument-hint: [task numbers separated by comma]
description: Execute multiple independent tasks in parallel using subagents
model: sonnet
---

# Parallel Tasks Skill

Launch multiple independent backlog tasks in parallel using subagents.

## Usage

- `/parallel-tasks` - Show independent tasks and ask which to run in parallel
- `/parallel-tasks 039,040,042` - Execute specific tasks in parallel

## Workflow

### 1. Identify Independent Tasks

Read all tasks from `docs/dev/backlog/`:

```bash
ls docs/dev/backlog/*.md
```

For each task, check:
- `Blocked by: -` (no dependencies)
- `Status: pending` (not already in progress)
- No file conflicts with other selected tasks

### 2. Detect File Conflicts

Parse "Files to Modify" section from each task. Tasks that modify the same files should NOT run in parallel.

Example conflict detection:
```
Task #039: modifies _css.py, _html.py, _js_core.py
Task #040: modifies config.py, api.py
Task #042: modifies api.py

Conflict: #040 and #042 both modify api.py
```

### 3. Present Selection

```
## Independent Tasks Available

| # | Task | Slice | Files | Parallelizable |
|---|------|-------|-------|----------------|
| 039 | Dark/Light Mode Toggle | Dashboard | _css.py, _html.py, _js_core.py | ✓ |
| 040 | RSS Feed Endpoint | Backend | config.py, api.py | ✓ |
| 042 | Status Badge SVG | Backend | api.py | ⚠️ conflicts with #040 |

Recommended parallel groups:
- Group A: #039 + #040 (no conflicts)
- Group B: #039 + #042 (no conflicts)

Which tasks to execute? (comma-separated, e.g., 039,040)
```

### 4. Update Task Status

For each selected task:

1. Update task file status to `in_progress`
2. Set `Started: [today's date]`
3. Add to Progress Log: `[timestamp] Started (parallel execution)`

### 5. Update INDEX.md

```markdown
## Current Focus

> **Parallel Execution Active**
> - Task #039: Dark/Light Mode Toggle (agent-1)
> - Task #040: RSS Feed Endpoint (agent-2)

## Quick Stats
- **In Progress**: 2 tasks
```

### 6. Launch Subagents

Use the Task tool to launch subagents in parallel:

```
For each selected task, launch a subagent with:
- subagent_type: backend-developer (for Backend tasks) or frontend-developer (for Frontend/Dashboard tasks)
- prompt: Task description + acceptance criteria + files to modify
- run_in_background: true
```

**CRITICAL**: Launch ALL subagents in a SINGLE message with multiple Task tool calls to ensure true parallel execution.

Example prompt for subagent:
```
Complete Task #039: Dark/Light Mode Toggle

## Acceptance Criteria
- [ ] Toggle button in header with sun/moon icon
- [ ] Theme preference stored in localStorage
...

## Files to Modify
- webstatuspi/_dashboard/_css.py
- webstatuspi/_dashboard/_html.py
- webstatuspi/_dashboard/_js_core.py

## Instructions
1. Read the existing files first
2. Implement each criterion
3. Run /lint and /test after implementation
4. Update the task file with progress
5. Mark checkboxes as you complete them

When done, report completion status.
```

### 7. Monitor Progress

After launching:
```
## Parallel Execution Started

| Task | Agent | Status | Output File |
|------|-------|--------|-------------|
| #039 | frontend-developer | running | /tmp/agent-039.txt |
| #040 | backend-developer | running | /tmp/agent-040.txt |

Use `Read` tool on output files to check progress.
Use `/complete-task` when agents finish.
```

### 8. Collect Results

When all agents complete:
```
## Parallel Execution Complete

| Task | Result | Duration |
|------|--------|----------|
| #039 | ✓ Success | 3m 42s |
| #040 | ✓ Success | 2m 15s |

All tasks completed successfully.
Run /test and /lint to verify.
```

## File Conflict Rules

Tasks that modify the same file CANNOT run in parallel:

| Conflict Type | Action |
|---------------|--------|
| Same file | Block parallel execution |
| Same module | Warn, allow with caution |
| Same slice | Allow (independent features) |

## Subagent Selection

| Task Slice | Subagent Type |
|------------|---------------|
| Dashboard, Frontend, UX | frontend-developer |
| Backend, API, Core | backend-developer |
| Database | database-specialist |
| DevOps, Config | backend-developer |
| Testing | qa-engineer |
| Docs | general-purpose |

## Error Handling

- **Agent fails**: Report error, mark task as blocked, continue others
- **File conflict detected mid-execution**: Stop conflicting agent, report
- **All agents fail**: Summarize errors, suggest manual intervention

## Completion

After parallel execution completes:

1. Run `/test` to verify all changes work together
2. Run `/lint` to check code quality
3. Use `/complete-task` for each successful task
4. Report any integration issues

## Example Full Flow

```bash
# User runs:
/parallel-tasks 039,040

# System:
1. Validates tasks are independent
2. Updates both task files to in_progress
3. Updates INDEX.md with parallel focus
4. Launches 2 subagents in parallel
5. Reports output file locations
6. User can monitor or wait
7. When done, reports results
8. User runs /complete-task for each
```
