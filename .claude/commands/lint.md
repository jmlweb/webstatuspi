---
argument-hint: [path]
description: Run linters (flake8, mypy) on Python code
model: haiku
---

# Lint Skill

Run code quality checks with flake8 and type checking with mypy.

## Usage

- `/lint` - Lint all Python files in src/
- `/lint src/monitor.py` - Lint specific file
- `/lint --fix` - Show auto-fixable issues

## Workflow

### 1. Check Tools Available

```bash
flake8 --version 2>/dev/null || echo "flake8 not installed"
mypy --version 2>/dev/null || echo "mypy not installed"
```

If tools missing:
```
⚠️ Linting tools not fully installed

Missing:
- mypy (type checking)

Install with:
pip install flake8 mypy

Continuing with available tools...
```

### 2. Run Flake8 (Style)

```bash
flake8 src/ \
    --max-line-length=100 \
    --ignore=E501,W503 \
    --statistics \
    --count
```

Configuration from `setup.cfg` or `.flake8` if exists.

### 3. Run Mypy (Types)

```bash
mypy src/ \
    --python-version 3.7 \
    --ignore-missing-imports \
    --show-error-codes \
    --no-error-summary
```

Configuration from `mypy.ini` or `pyproject.toml` if exists.

### 4. Parse and Categorize Issues

Group by severity:
- **Errors**: Type mismatches, undefined names
- **Warnings**: Unused imports, shadowed names
- **Style**: Line length, spacing

### 5. Report Results

**Clean code:**
```
✓ Linting passed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Flake8:  0 issues
Mypy:    0 errors
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

All files clean!
```

**With issues:**
```
⚠️ Linting found issues

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Flake8:  3 issues
Mypy:    2 errors
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Errors (fix required)

1. src/monitor.py:45 [mypy:arg-type]
   Argument 1 to "check_url" has incompatible type "int"; expected "str"

2. src/api.py:23 [mypy:return-value]
   Incompatible return value type (got "None", expected "dict")

## Warnings

3. src/config.py:12 [F401]
   'os' imported but unused

4. src/database.py:5 [F401]
   'typing.Dict' imported but unused

## Style (optional)

5. src/monitor.py:78 [E302]
   Expected 2 blank lines, found 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fix errors before committing.
Warnings and style issues are optional.
```

### 6. Auto-fix Suggestions

For fixable issues:
```
## Auto-fixable Issues

The following can be fixed automatically:

1. Unused imports (3 occurrences)
   autopep8 --in-place --select=F401 src/

2. Blank line issues (2 occurrences)
   autopep8 --in-place --select=E302,E303 src/

Run fixes? (yes/no/manual)
```

## Configuration Files

### .flake8
```ini
[flake8]
max-line-length = 100
ignore = E501,W503
exclude = venv,__pycache__
per-file-ignores =
    __init__.py:F401
```

### mypy.ini
```ini
[mypy]
python_version = 3.7
ignore_missing_imports = True
strict_optional = True
warn_unused_ignores = True
```

## Integration with Git

Before commit suggestion:
```
ℹ️ Pre-commit Check

Found 2 errors in staged files:
- src/monitor.py (modified, staged)
- src/api.py (modified, staged)

Fix before committing? (yes/no/ignore)
```

## Pi 1B+ Specific Checks

Additional checks for Raspberry Pi compatibility:

```
## Pi Compatibility Warnings

1. src/display.py:15
   Using PIL.Image - memory intensive on Pi 1B+
   Consider: Limit image size to 128x64

2. src/api.py:45
   ThreadingMixIn may cause memory growth
   Consider: Limit max workers to 2
```

## Error Handling

- Flake8 not found: Skip style checks, continue with mypy
- Mypy not found: Skip type checks, continue with flake8
- Both missing: Show installation instructions
- Parse errors: Show raw tool output
