---
argument-hint:
description: Verify documentation matches implementation
model: sonnet
---

# Sync Docs Skill

Verify that documentation accurately reflects the current implementation.

## Usage

- `/sync-docs` - Full documentation audit
- `/sync-docs api` - Check only API documentation
- `/sync-docs config` - Check only configuration documentation

## Workflow

### 1. Identify Documentation Files

```
docs/
├── ARCHITECTURE.md    # System design
├── HARDWARE.md        # Hardware specs
└── testing/           # Test guidelines

README.md              # User guide, API reference
AGENTS.md              # Development rules
```

### 2. Extract Documented Claims

Parse documentation for verifiable claims:

**From README.md:**
- API endpoints listed
- Configuration options documented
- CLI arguments described
- Environment variables mentioned

**From ARCHITECTURE.md:**
- Module responsibilities
- Database schema
- Data flow descriptions

**From AGENTS.md:**
- Code conventions
- File structure
- Naming patterns

### 3. Verify Against Implementation

For each documented claim, check if it matches reality:

**API Endpoints:**
```python
# From README: GET /api/stats
# Check: grep -r "GET.*stats" src/api.py
```

**Configuration Options:**
```python
# From README: interval: polling interval in seconds
# Check: grep -r "interval" src/config.py
```

**Database Schema:**
```python
# From ARCHITECTURE: checks table with columns (id, url_name, ...)
# Check: grep -r "CREATE TABLE checks" src/database.py
```

### 4. Report Findings

```
## Documentation Sync Report

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Checked: 4 documents, 47 claims
Passed:  42 claims
Issues:  5 claims
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Issues Found

### README.md

1. **Missing endpoint** (line 45)
   Documented: GET /api/stats/{url_name}
   Reality: Endpoint not implemented
   Action: Implement or remove from docs

2. **Outdated parameter** (line 78)
   Documented: --verbose flag
   Reality: Flag is --debug
   Action: Update documentation

### ARCHITECTURE.md

3. **Schema mismatch** (line 112)
   Documented: checks.response_time INTEGER
   Reality: checks.response_time_ms REAL
   Action: Update schema documentation

### AGENTS.md

4. **Outdated convention** (line 34)
   Documented: Use dataclasses for all DTOs
   Reality: Some use TypedDict
   Action: Update convention or fix code

5. **Missing slice** (line 156)
   Documented slices: Config, Core, Database, API, Hardware
   Reality: Also has Display slice
   Action: Add Display to slice reference

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 5. Suggest Fixes

For each issue, provide specific fix:

```
## Suggested Fixes

### Fix 1: README.md line 45
Remove undocumented endpoint or implement it:

Option A - Remove from docs:
```diff
- - `GET /api/stats/{url_name}` - Stats for specific URL
```

Option B - Implement endpoint:
Add to src/api.py around line 67

### Fix 2: README.md line 78
```diff
- Use `--verbose` for debug output
+ Use `--debug` for debug output
```

Apply fixes? (all/select/manual)
```

### 6. Check for Undocumented Features

Find implemented but undocumented features:

```
## Undocumented Features

The following are implemented but not documented:

1. **API Endpoint**: GET /api/health
   Location: src/api.py:23
   Suggest: Add to README API Reference

2. **Config Option**: retry_count
   Location: src/config.py:45
   Suggest: Add to Configuration section

3. **CLI Flag**: --config-path
   Location: src/main.py:12
   Suggest: Add to Usage section

Document these features? (yes/no/select)
```

## Specific Checks

### API Documentation (`/sync-docs api`)

Focus on:
- All endpoints listed
- Request/response formats accurate
- Status codes documented
- Error responses documented

### Configuration Documentation (`/sync-docs config`)

Focus on:
- All config keys documented
- Default values accurate
- Type information correct
- Required vs optional clear

### Architecture Documentation (`/sync-docs arch`)

Focus on:
- Module descriptions accurate
- Dependencies listed
- Database schema current
- Data flow diagrams match code

## Integration with Task System

After sync check:
```
ℹ️ Documentation tasks may be needed

Consider creating tasks for:
- Update README API reference (3 changes)
- Update ARCHITECTURE schema (1 change)

Use /add-task to create documentation tasks.
```

## Error Handling

- Documentation file missing: Note as issue
- Parse error in markdown: Show location
- Ambiguous claims: Skip with note
- Large diff: Summarize changes
