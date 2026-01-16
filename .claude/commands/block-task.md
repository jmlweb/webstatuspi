---
argument-hint: [task number] [reason]
description: Mark a task as blocked with reason
model: haiku
---

# Block Task Skill

Mark a task as blocked, document the reason, and suggest alternatives.

## Usage

- `/block-task 003 "waiting for hardware"` - Block with reason
- `/block-task 003` - Block current task, ask for reason
- `/block-task` - Block active task, ask for reason

## Workflow

### 1. Identify Task

If no task number:
- Use current active task from INDEX.md
- If no active task, show error

### 2. Get Block Reason

If reason not provided, ask:
- "Why is this task blocked?"
- Suggest common reasons:
  - Waiting for dependency task #XXX
  - Waiting for external input
  - Hardware not available
  - Need clarification on requirements
  - Technical blocker discovered

### 3. Determine Blocker Type

Analyze reason to categorize:

| Type | Example | Action |
|------|---------|--------|
| Task dependency | "needs #002 first" | Link to blocking task |
| External | "waiting for hardware" | Document in notes |
| Technical | "memory limit issue" | May need learning |
| Clarification | "unclear requirements" | Tag for user input |

### 4. Update Task File

```markdown
## Metadata
- **Status**: blocked  # Changed
- **Priority**: P3  # Demote from P1 if was active
- **Blocked by**: #002 | "external: hardware" | "clarification needed"
```

Add to Progress Log:
```markdown
## Progress Log
- [YYYY-MM-DD HH:MM] Blocked: [reason]
```

Add blocking details to Implementation Notes if technical:
```markdown
## Implementation Notes
### Blocker (added YYYY-MM-DD)
[Detailed description of what's blocking progress]
```

### 5. Update INDEX.md

1. **Quick Stats**: Adjust if was in_progress
   ```markdown
   - **In Progress**: 0 tasks
   ```

2. **Current Focus**: Clear if was active
   ```markdown
   ## Current Focus
   > No active task. Task #XXX blocked.
   ```

3. **Backlog Table**: Mark as blocked
   ```markdown
   | XXX | [title] | [slice] | BLOCKED |
   ```

### 6. Suggest Alternatives

```
⚠️ Task #XXX is now blocked

Reason: [reason]

## Available Tasks (unblocked)
| # | Task | Priority |
|---|------|----------|
| 004 | Alternative task | P2 |
| 005 | Another option | P3 |

Use /start-task 004 to work on an alternative
```

### 7. If Technical Blocker

Prompt for learning:
```
This appears to be a technical blocker. Would you like to:
1. Add a learning about this issue (/add-learning)
2. Continue without documenting
3. Create a new task to resolve the blocker

Technical blockers often contain valuable learnings!
```

## Block Reason Formats

### Task Dependency
```markdown
- **Blocked by**: #002
```

### External Dependency
```markdown
- **Blocked by**: external: [description]
```

### Needs Clarification
```markdown
- **Blocked by**: clarification: [question]
```

### Technical Issue
```markdown
- **Blocked by**: technical: [brief description]
```

## Unblocking

When a blocker is resolved:
1. Edit task file: Change status back to `pending`
2. Remove or update "Blocked by" field
3. Add Progress Log entry: "Unblocked: [resolution]"
4. Use `/start-task` to resume

## Error Handling

- No active task and no argument: Show pending/blocked tasks
- Task already blocked: Show current blocker, ask to update
- Task completed: Cannot block completed tasks
