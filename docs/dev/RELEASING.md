# Releasing WebStatusPi

This document describes the release process for WebStatusPi.

## Overview

WebStatusPi uses GitHub Actions for automated releases. When a version tag is pushed, the release workflow automatically:

1. Builds the Python package (wheel and source distribution)
2. Generates a changelog from commit history
3. Creates a GitHub Release with the built artifacts

## Tag Format

Tags must follow semantic versioning with a `v` prefix:

```
v{MAJOR}.{MINOR}.{PATCH}
```

Examples:
- `v0.1.0` - Initial release
- `v0.2.0` - New features added
- `v0.2.1` - Bug fixes
- `v1.0.0` - First stable release

## Release Process

### 1. Update Version

Update the version in `pyproject.toml`:

```toml
[project]
version = "X.Y.Z"
```

### 2. Commit Version Change

```bash
git add pyproject.toml
git commit -m "chore: bump version to vX.Y.Z"
```

### 3. Create and Push Tag

```bash
git tag vX.Y.Z
git push origin main
git push origin vX.Y.Z
```

### 4. Verify Release

1. Go to [GitHub Actions](https://github.com/jmlweb/webstatuspi/actions)
2. Check the "Release" workflow completes successfully
3. Verify the release appears in [Releases](https://github.com/jmlweb/webstatuspi/releases)

## Changelog Generation

The release workflow automatically generates a changelog from commits since the last tag. For better changelogs, use conventional commit messages:

| Prefix | Description |
|--------|-------------|
| `feat:` | New features |
| `fix:` | Bug fixes |
| `docs:` | Documentation |
| `refactor:` | Code refactoring |
| `test:` | Tests |
| `chore:` | Maintenance |

Example commits:
```
feat(api): add /health endpoint
fix(monitor): handle connection timeouts
docs: update installation guide
```

## Pre-release Checklist

Before creating a release tag:

- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Linting passes (`flake8 webstatuspi tests`)
- [ ] Type checking passes (`mypy webstatuspi`)
- [ ] Version updated in `pyproject.toml`
- [ ] Changes tested locally

## CI Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `lint.yml` | Push/PR to main | Run flake8 and mypy |
| `test.yml` | Push/PR to main | Run tests on Python 3.11, 3.12, 3.13 |
| `release.yml` | Tag `v*.*.*` | Build and publish release |

## Troubleshooting

### Release workflow failed

1. Check the workflow logs in GitHub Actions
2. Common issues:
   - Invalid tag format (must be `vX.Y.Z`)
   - Build errors (test locally first)
   - Permission issues (check repository settings)

### Missing artifacts

If the release was created but artifacts are missing:
1. Check the build step in the workflow logs
2. Verify `pyproject.toml` is valid
3. Re-run the workflow or manually upload artifacts
