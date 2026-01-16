---
argument-hint: [test-path]
description: Run tests with coverage report
model: haiku
---

# Test Skill

Run project tests with pytest and generate coverage report.

## Usage

- `/test` - Run all tests
- `/test tests/test_monitor.py` - Run specific test file
- `/test -k "test_check_url"` - Run tests matching pattern

## Workflow

### 1. Check Test Environment

```bash
# Verify pytest is available
python3 -m pytest --version 2>/dev/null || echo "pytest not installed"
```

If pytest not installed:
```
⚠️ pytest not installed

Install test dependencies:
pip install pytest pytest-mock coverage

Or add to requirements-dev.txt
```

### 2. Run Tests

**Default (all tests with coverage):**
```bash
python3 -m pytest tests/ \
    --tb=short \
    -v \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html:coverage_html
```

**Specific file:**
```bash
python3 -m pytest tests/test_monitor.py -v --tb=short
```

**Pattern match:**
```bash
python3 -m pytest tests/ -k "test_check_url" -v --tb=short
```

### 3. Parse Results

Extract from pytest output:
- Total tests run
- Passed / Failed / Skipped counts
- Coverage percentage
- Uncovered lines

### 4. Report Results

**All passing:**
```
✓ Tests passed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests:    12 passed, 0 failed, 2 skipped
Coverage: 87% (src/)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Uncovered lines:
- src/api.py: 45-48 (error handler)
- src/database.py: 112-115 (migration)

Coverage report: coverage_html/index.html
```

**With failures:**
```
❌ Tests failed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests:    10 passed, 2 failed, 2 skipped
Coverage: 85% (src/)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Failed tests:
1. test_monitor.py::test_check_url_timeout
   AssertionError: Expected timeout after 5s, got 10s
   File: tests/test_monitor.py:45

2. test_api.py::test_stats_endpoint
   KeyError: 'success_count'
   File: tests/test_api.py:78

Fix failures before committing.
```

### 5. Suggest Actions

Based on results:

**If coverage dropped:**
```
⚠️ Coverage decreased

Previous: 90%
Current:  85%

New uncovered code:
- src/monitor.py:67-72 (new function)

Consider adding tests for new code.
```

**If new test file needed:**
```
ℹ️ Untested module detected

src/buzzer.py has no corresponding test file.

Create tests/test_buzzer.py? (yes/no)
```

## Quick Test Modes

### Smoke Test (fast)
```bash
python3 -m pytest tests/ -x -q --tb=line
```
- Stops on first failure
- Minimal output
- For quick validation

### Full Test (CI-like)
```bash
python3 -m pytest tests/ \
    -v \
    --strict-markers \
    --cov=src \
    --cov-fail-under=80
```
- Verbose output
- Strict marker checking
- Fails if coverage < 80%

## Integration with Task System

After running tests:
```
Tests completed. Related tasks:

#004 OLED display driver - has test: tests/test_display.py ✓
#005 Button handling - no tests yet ⚠️

Use /check-task to verify implementation status.
```

## Error Handling

- No tests directory: Create basic structure
- Import errors: Check PYTHONPATH and dependencies
- Fixture errors: Show fixture definition location
- Timeout: Suggest increasing timeout or checking for infinite loops
