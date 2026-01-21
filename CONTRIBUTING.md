# Contributing to WebStatusPi

Thank you for your interest in contributing to WebStatusPi! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Pull Request Process](#pull-request-process)
- [Code Style](#code-style)

## Code of Conduct

This project follows a simple code of conduct:

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Keep discussions technical and on-topic

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check [existing issues](https://github.com/jmlweb/webstatuspi/issues) to avoid duplicates.

When reporting a bug, include:

- **Environment**: Raspberry Pi model, OS version, Python version
- **Steps to reproduce**: Clear, numbered steps
- **Expected behavior**: What you expected to happen
- **Actual behavior**: What actually happened
- **Logs/Output**: Relevant console output or error messages
- **Configuration**: Your `config.yaml` (redact sensitive URLs if needed)

### Suggesting Features

Feature suggestions are welcome! Please:

1. Check [existing issues](https://github.com/jmlweb/webstatuspi/issues) for similar suggestions
2. Open a new issue with the `enhancement` label
3. Describe the use case and why it would be useful
4. Consider the [hardware constraints](docs/HARDWARE.md) (Pi 1B+ has limited resources)

### Submitting Code

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes following the [code style](#code-style)
4. Write/update tests as needed
5. Ensure all tests pass
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.11+ (required for modern language features)
- SQLite3 (usually pre-installed)
- Git

### Setup Steps

```bash
# 1. Fork and clone the repository
git clone https://github.com/<your-username>/webstatuspi.git
cd webstatuspi

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install development dependencies
pip install -e .[dev]

# 4. Create your configuration file
cp config.example.yaml config.yaml
# Edit config.yaml with your test URLs

# 5. Run the application
python -m webstatuspi
```

### Development Without a Raspberry Pi

You can develop and test without physical hardware using mocks:

```bash
# Run with hardware mocks enabled
MOCK_GPIO=true MOCK_DISPLAY=true python -m webstatuspi
```

See [docs/testing/MOCKING.md](docs/testing/MOCKING.md) for detailed mocking documentation.

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_monitor.py

# Run with coverage report
pytest --cov=webstatuspi --cov-report=html

# Open coverage report (macOS)
open htmlcov/index.html
```

### Test Categories

- `tests/test_config.py` - Configuration loading and validation
- `tests/test_database.py` - Database operations
- `tests/test_monitor.py` - URL monitoring logic
- `tests/test_api.py` - API endpoints

## Pull Request Process

### Before Submitting

1. **Run linters**: Ensure code passes ruff checks
   ```bash
   ruff check .
   ruff format --check .
   ```
2. **Update tests**: Add or modify tests for your changes
3. **Run tests**: Ensure all tests pass (`pytest`)
4. **Update docs**: If your change affects user-facing behavior, update relevant documentation

> **Tip**: Install the pre-commit hook to run linters automatically before each commit:
> ```bash
> pre-commit install
> ```

### PR Guidelines

- **One feature per PR**: Keep PRs focused and reviewable
- **Clear title**: Use a descriptive title (e.g., "Add timeout configuration per URL")
- **Description**: Explain what changes you made and why
- **Link issues**: Reference related issues (e.g., "Fixes #123")

### PR Template

```markdown
## Summary
Brief description of the changes.

## Changes
- Change 1
- Change 2

## Testing
How did you test these changes?

## Related Issues
Fixes #issue_number (if applicable)
```

### Review Process

1. A maintainer will review your PR
2. Address any feedback or requested changes
3. Once approved, a maintainer will merge your PR

## Code Style

This project follows specific coding conventions optimized for the Raspberry Pi 1B+ constraints.

**For detailed code style guidelines, see [AGENTS.md](AGENTS.md).**

### Quick Reference

- **Type hints**: Required for all functions. Use Python 3.11+ syntax: `list[str]` not `List[str]`, `X | None` not `Optional[X]`
- **Functional approach**: Prefer functions over classes for logic
- **Naming**: `snake_case` for functions/variables, `PascalCase` for types
- **Imports**: Standard library first, then third-party, then local (alphabetically sorted)
- **Line length**: Maximum 120 characters
- **Dependencies**: Minimal - avoid adding new dependencies without discussion
- **Linting**: Code must pass `ruff check` and `ruff format`

### Example

```python
from dataclasses import dataclass


@dataclass
class CheckResult:
    """Result of a URL health check."""

    url: str
    status_code: int | None
    response_time_ms: int
    is_success: bool
    error_message: str | None = None


def check_url(url: str, timeout: int = 10) -> CheckResult:
    """Check if a URL is accessible and return the result."""
    # Implementation...
```

## Questions?

If you have questions about contributing, feel free to:

- Open an issue with the `question` label
- Check the [documentation](docs/)

Thank you for contributing!
