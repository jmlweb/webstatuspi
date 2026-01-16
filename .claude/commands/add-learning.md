---
argument-hint: [learning description]
description: Add a learning to LEARNINGS.md
model: haiku
---

# Add Learning Skill

Document a discovery or insight in the project's knowledge base.

## CRITICAL: When to Use This Skill

**Agents MUST call /add-learning immediately when:**

1. **Discovering unexpected behavior**
   - Library works differently than documented
   - API has undocumented quirks
   - Hardware behaves unexpectedly

2. **Finding a solution to a problem**
   - Workaround for a bug
   - Configuration that fixed an issue
   - Correct way to use a feature

3. **Learning project-specific patterns**
   - How existing code handles X
   - Convention used in this codebase
   - Integration patterns between components

4. **Encountering Pi 1B+ constraints**
   - Memory limitations
   - Performance optimizations needed
   - Library compatibility issues

**DO NOT wait until task completion. Document immediately.**

## Usage

- `/add-learning "luma.oled requires I2C permissions"` - Quick add
- `/add-learning` - Interactive mode (asks questions)

## Workflow

### 1. Gather Learning Details

If not provided as argument, ask:

1. **What did you discover?** (brief title)
2. **What were you trying to do?** (context)
3. **What did you learn?** (the insight)
4. **How did you apply it?** (action taken)

### 2. Determine Category

Categorize the learning:

| Category | Examples |
|----------|----------|
| Hardware | I2C, GPIO, display, sensors |
| Performance | Memory, threading, optimization |
| Configuration | YAML, settings, environment |
| Database | SQLite, queries, schema |
| API | HTTP server, endpoints, JSON |
| Dependencies | Libraries, pip, compatibility |

### 3. Get Context

- Current active task (from INDEX.md)
- Today's date
- Next learning ID (scan LEARNINGS.md for highest LXXX)

### 4. Format Learning

```markdown
### LXXX: [Brief title]
**Date**: YYYY-MM-DD
**Task**: #XXX [task name] (or "General" if no active task)
**Context**: [What was being attempted]
**Learning**: [What was discovered]
**Action**: [How it was applied/documented]
```

### 5. Update LEARNINGS.md

1. Read current `docs/dev/LEARNINGS.md`
2. Find appropriate category section
3. Insert new learning after section header
4. Maintain consistent formatting

### 6. Optionally Update Task

If there's an active task:
- Add brief note to task's Learnings section
- Reference the learning ID: "See LXXX in LEARNINGS.md"

### 7. Confirm

```
✓ Added learning LXXX to LEARNINGS.md

Category: Hardware
Title: luma.oled requires I2C permissions

Referenced from task #004 (if applicable)
```

## Learning Quality Guidelines

### Good Learnings

```markdown
### L005: ThreadingMixIn causes memory growth over 24h
**Date**: 2026-01-16
**Task**: #004 API server
**Context**: Testing API server stability over extended period
**Learning**: http.server ThreadingMixIn doesn't clean up threads properly,
causing ~1MB/hour memory growth. Need to limit thread pool.
**Action**: Implemented max_workers=2 limit in api.py, added thread cleanup
```

### Bad Learnings (too vague)

```markdown
### L005: Threading is tricky
**Date**: 2026-01-16
**Task**: #004
**Context**: Working on API
**Learning**: Threads cause problems
**Action**: Fixed it
```

## Quick Add Format

For rapid documentation during work:

```
/add-learning "SSD1306 reset pin not needed on cheap modules - can pass None"
```

Will be expanded to full format with:
- Auto-detected category (Hardware)
- Current task context
- Prompted for action if not obvious

## Integration with Task Workflow

```
┌─────────────────┐
│  Working on     │
│  Task #004      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Discover       │
│  something      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  /add-learning  │◄──── DO THIS IMMEDIATELY
│  "discovery"    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Continue       │
│  working        │
└─────────────────┘
```

## Error Handling

- LEARNINGS.md doesn't exist: Create it with template
- Category not found: Add new category section
- Duplicate learning: Warn and ask to update existing
- No active task: Mark as "General" context
