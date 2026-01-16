# Development Learnings

This file captures lessons learned during development. Each learning has a unique ID for reference.

## Index by Category
- [Hardware](#hardware)
- [Performance](#performance)
- [Configuration](#configuration)
- [Database](#database)
- [API](#api)

---

## Hardware

(No learnings yet)

---

## Performance

(No learnings yet)

---

## Configuration

### L001: Manual YAML parsing is sufficient for config loading
**Date**: 2026-01-16
**Task**: #001 Config loader with dataclasses
**Context**: Needed to convert YAML config to dataclasses while minimizing dependencies for Pi 1B+
**Learning**: Manual YAML→dataclass conversion is straightforward and avoids adding dependencies like `dacite`. Simple factory functions work well for parsing each config section.
**Action**: Implemented manual parsing functions (`_parse_url_config`, `_parse_database_config`, etc.) in `src/config.py`

### L002: Dataclass __post_init__ enables immutable validation
**Date**: 2026-01-16
**Task**: #001 Config loader with dataclasses
**Context**: Needed to validate config values while keeping dataclasses immutable
**Learning**: Python's `__post_init__` method works perfectly with `frozen=True` dataclasses. Validation runs after initialization but before the object is frozen, allowing us to enforce constraints while maintaining immutability.
**Action**: Added validation logic in `__post_init__` methods for all config dataclasses

---

## Database

(No learnings yet)

---

## API

(No learnings yet)

---

## Learning Template

When adding a new learning, use this format:

```markdown
### LXXX: Brief title describing the learning
**Date**: YYYY-MM-DD
**Task**: #XXX Task name
**Context**: What were you trying to do?
**Learning**: What did you discover?
**Action**: How was this documented/applied?
```
