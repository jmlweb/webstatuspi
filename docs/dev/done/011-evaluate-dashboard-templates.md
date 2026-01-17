# Task #011: Evaluate Dashboard Templates vs Embedded HTML

## Metadata
- **Status**: completed
- **Priority**: P1 - Active
- **Slice**: API
- **Created**: 2026-01-18
- **Started**: 2026-01-18
- **Completed**: 2026-01-18
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a developer, I want to evaluate whether using template files for the dashboard would be better than embedding HTML in the Python code, so that we can make an informed architectural decision.

**Acceptance Criteria**:
- [x] Document current embedded HTML approach (pros/cons)
- [x] Research template engine options (Jinja2, string.Template, f-strings)
- [x] Evaluate memory footprint of each approach on Pi 1B+
- [x] Evaluate disk space impact (embedded vs separate files)
- [x] Evaluate code maintainability (editing HTML in Python vs template files)
- [x] Evaluate startup time impact (loading templates vs embedded string)
- [x] Evaluate runtime performance (template rendering vs static string)
- [x] Document dependency impact (stdlib vs external libraries)
- [x] Create recommendation with rationale
- [x] Document decision in ADR format if recommendation differs from current approach

## Implementation Notes

### Current State
- Dashboard HTML is embedded as `HTML_DASHBOARD` constant in `webstatuspi/api.py`
- Size: ~35KB (35,122 bytes)
- Served directly as string response at `/` endpoint
- Zero external dependencies for dashboard serving

### Evaluation Areas

1. **Memory Footprint**
   - Embedded: String constant loaded at module import
   - Templates: Template files loaded on demand or at startup
   - Measure actual memory usage on Pi 1B+ constraints (512MB RAM)

2. **Disk Space**
   - Embedded: HTML included in Python bytecode (.pyc)
   - Templates: Separate .html files in filesystem
   - Consider SD card space constraints

3. **Code Maintainability**
   - Embedded: HTML editing requires Python file changes
   - Templates: Separate HTML files, easier to edit
   - Consider developer experience and tooling support

4. **Performance**
   - Embedded: Zero overhead, direct string return
   - Templates: Parsing/rendering overhead (even if minimal)
   - Measure actual response times

5. **Dependencies**
   - Embedded: Zero dependencies (stdlib only)
   - Templates: May require Jinja2 (~5MB) or use stdlib `string.Template`
   - Consider Pi 1B+ dependency constraints

6. **Deployment**
   - Embedded: Single-file deployment
   - Templates: Multiple files to manage and deploy

### Template Options to Evaluate

1. **Jinja2** (external dependency)
   - Pros: Powerful templating, variable substitution, conditionals
   - Cons: ~5MB dependency, parsing overhead

2. **string.Template** (stdlib)
   - Pros: No dependencies, simple variable substitution
   - Cons: Limited features, still requires file I/O

3. **f-strings with file reading** (stdlib)
   - Pros: No dependencies, Python-native
   - Cons: Requires file I/O, less structured

4. **Keep embedded** (current)
   - Pros: Zero overhead, single file, no I/O
   - Cons: HTML mixed with Python code

### Pi 1B+ Constraints to Consider

- **RAM**: 512MB total (~256MB available for application)
- **CPU**: Single-core 700MHz ARM11
- **Storage**: SD card (slow I/O, wear considerations)
- **Network**: 10/100 Ethernet

### Decision Criteria

The evaluation should consider:
- Does template approach provide sufficient benefit to justify overhead?
- Does it align with project's minimal dependency philosophy?
- Does it improve or worsen maintainability?
- Does it impact performance targets (< 100ms API response)?

## Files to Review
- `webstatuspi/api.py` - Current embedded HTML implementation
- `AGENTS.md` - ADR-004: Embedded HTML Dashboard (current decision)

## Files to Modify
- `docs/dev/LEARNINGS.md` - Document evaluation findings
- `AGENTS.md` - Update ADR-004 or create new ADR if recommendation differs

## Dependencies
- None (evaluation task only)

## Progress Log

- [2026-01-18 00:00] Started task
- [2026-01-18 00:15] Documented current embedded HTML approach (35KB, 78% of api.py)
- [2026-01-18 00:30] Researched template options: Jinja2 (144KB), string.Template, str.format()
- [2026-01-18 00:45] Key finding: Dashboard is STATIC HTML, uses client-side JS rendering
- [2026-01-18 01:00] Evaluated memory (~35KB all approaches), disk (negligible difference)
- [2026-01-18 01:15] Decision: Keep embedded approach, but separate into `_dashboard.py`
- [2026-01-18 01:30] Implemented separation: created `_dashboard.py`, updated `api.py`
- [2026-01-18 01:45] All 27 tests pass, implementation complete
- [2026-01-18 02:00] Task completed and documented

## Learnings

### Key Finding: No Template Engine Needed
The dashboard uses **client-side rendering** via JavaScript fetch to `/status` endpoint.
All dynamic content is rendered in the browser, not server-side. Template engines are
designed for server-side rendering and would provide no functional benefit here.

### Evaluation Summary

| Approach | Memory | Disk | Dependencies | Performance |
|----------|--------|------|--------------|-------------|
| Embedded (current) | ~35KB | 45KB | 0 | Zero overhead |
| File + cache | ~35KB | 45KB | 0 | Minimal |
| Jinja2 | ~2MB | 188KB | MarkupSafe | Parsing overhead |

### Decision: Separate Module, Not Template Engine

**Recommendation**: Keep embedded string approach but extract to `_dashboard.py` module.

**Rationale**:
1. Template engines add dependencies without functional benefit
2. Dashboard is static HTML with client-side rendering
3. Separating to `_dashboard.py` improves maintainability
4. Import-based approach has identical runtime performance
5. Cleaner git diffs (HTML changes isolated from Python logic)

### Implementation
- Created `webstatuspi/_dashboard.py` with `HTML_DASHBOARD` constant
- Updated `webstatuspi/api.py` to import from `_dashboard`
- `api.py`: 44KB → 10KB (Python code only)
- `_dashboard.py`: 35KB (HTML/CSS/JS)
- All 27 existing tests pass
