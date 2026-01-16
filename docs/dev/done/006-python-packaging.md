# Task #006: Python Packaging Files

## Metadata
- **Status**: completed
- **Priority**: P1 - Active
- **Slice**: Config
- **Created**: 2026-01-16
- **Started**: 2026-01-16
- **Completed**: 2026-01-16
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a Pi operator, I want proper Python packaging so that I can easily install WebStatusPi on the Raspberry Pi with `pip install` and have reproducible dependencies.

**Acceptance Criteria**:
- [x] `pyproject.toml` created with project metadata and dependencies
- [x] Runtime dependencies declared (PyYAML>=6.0.1, requests>=2.31.0)
- [x] Dev dependencies declared as optional extras (pytest, pytest-mock, coverage)
- [x] CLI entry point configured (`webstatuspi` command)
- [x] `requirements.txt` generated for compatibility
- [x] `.python-version` file added (Python 3.7+)
- [x] `src/__main__.py` created for `python -m webstatuspi` support
- [x] Installation verified: `pip install .` works and command runs

## Implementation Notes

Currently missing standard Python packaging files which impacts exportability:
- No `requirements.txt` - can't reproduce dependencies
- No `pyproject.toml` - can't install as package
- No `requirements-dev.txt` - dev dependencies undeclared
- No `__main__.py` - can't run via `python -m webstatuspi`
- No `.python-version` - Python version not pinned

The project follows a minimal dependency strategy (stdlib-first, only 2 runtime deps), but needs proper packaging for deployment to the Raspberry Pi 1B+.

## Files to Create/Modify
- `pyproject.toml` (create) - PEP 621 project metadata
- `requirements.txt` (create) - Generated from pyproject.toml
- `requirements-dev.txt` (create) - Development dependencies
- `.python-version` (create) - Pin to 3.7 (Pi compatibility)
- `src/__main__.py` (create) - Entry point for module execution
- `README.md` (update) - Add installation instructions

## Dependencies
None (foundational infrastructure task)

## Progress Log
- [2026-01-16 00:00] Started task
- [2026-01-16 23:56] Created pyproject.toml with PEP 621 metadata
- [2026-01-16 23:56] Renamed src/ directory to webstatuspi/ for proper package structure
- [2026-01-16 23:56] Created requirements.txt and requirements-dev.txt
- [2026-01-16 23:56] Created .python-version pinned to 3.7.0
- [2026-01-16 23:56] Created webstatuspi/__main__.py for `python -m webstatuspi` support
- [2026-01-16 23:56] Updated __init__.py with main() entry point
- [2026-01-16 23:56] Created setup.cfg for backwards compatibility and setuptools configuration
- [2026-01-16 23:56] Created setup.py as PEP 517 build backend
- [2026-01-16 23:56] Updated README.md with modern installation instructions
- [2026-01-16 23:56] Verified installation: `pip install .` and `pip install .[dev]` work correctly
- [2026-01-16 23:56] All runtime and dev dependencies install correctly

## Learnings
- **PEP 621 pyproject.toml** works well with modern setuptools but older pip (< 21.3) needs setup.cfg for full compatibility
- **Dual configuration** (pyproject.toml + setup.cfg) ensures maximum compatibility across Python versions and pip installations
- **Package discovery** requires setuptools to find the webstatuspi directory, so src/ layout was changed to flat layout
- **Entry points** need to be defined in setup.cfg for older pip versions to correctly create console scripts
- **Optional dependencies** using [project.optional-dependencies] in pyproject.toml are correctly resolved with setup.cfg's [options.extras_require]
