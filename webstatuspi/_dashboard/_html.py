"""HTML template for the dashboard.

This module loads the HTML template from dashboard.html and reads CSS/JS from
static files, providing a function to build the complete HTML.

All files support hot-reload: changes are detected automatically without
requiring a server restart.
"""

from pathlib import Path
from string import Template

_STATIC_DIR = Path(__file__).parent / "static"
_TEMPLATE_PATH = Path(__file__).parent / "dashboard.html"

# File paths for static assets
_STATIC_FILES = {
    "css": _STATIC_DIR / "styles.css",
    "js_utils": _STATIC_DIR / "utils.js",
    "js_charts": _STATIC_DIR / "charts.js",
    "js_core": _STATIC_DIR / "core.js",
}

# Cache for template and static files with their mtimes
_template_cache: Template | None = None
_template_mtime: float = 0.0
_static_cache: dict[str, str] = {}
_static_mtimes: dict[str, float] = {}
# Cache for binary static files (PNG, etc.)
_static_binary_cache: dict[str, bytes] = {}
_static_binary_mtimes: dict[str, float] = {}


def _get_template() -> Template:
    """Get the HTML template, reloading if the file changed.

    Uses file modification time to detect changes, minimizing I/O
    (only a stat() call per request, file read only when changed).

    Returns:
        The current Template instance.
    """
    global _template_cache, _template_mtime

    current_mtime = _TEMPLATE_PATH.stat().st_mtime

    if _template_cache is None or current_mtime != _template_mtime:
        _template_cache = Template(_TEMPLATE_PATH.read_text(encoding="utf-8"))
        _template_mtime = current_mtime

    return _template_cache


def _get_static_file(key: str) -> str:
    """Get static file content, reloading if the file changed.

    Uses file modification time to detect changes for hot-reload support.

    Args:
        key: The key identifying the static file (e.g., "css", "js_utils")

    Returns:
        The current file content as a string.
    """
    path = _STATIC_FILES[key]
    current_mtime = path.stat().st_mtime

    if key not in _static_cache or current_mtime != _static_mtimes.get(key):
        _static_cache[key] = path.read_text(encoding="utf-8")
        _static_mtimes[key] = current_mtime

    return _static_cache[key]


def get_static_asset(filename: str, binary: bool = False) -> str | bytes | None:
    """Get a static asset file by name, reloading if changed.

    Supports hot-reload: changes are detected automatically without server restart.

    Args:
        filename: Name of the file in the static directory (e.g., "logo-desktop.svg").
        binary: If True, return bytes; if False, return string (UTF-8).

    Returns:
        File content as string or bytes, or None if file doesn't exist.
    """
    path = _STATIC_DIR / filename

    if not path.exists():
        return None

    current_mtime = path.stat().st_mtime

    if binary:
        if filename not in _static_binary_cache or current_mtime != _static_binary_mtimes.get(filename):
            _static_binary_cache[filename] = path.read_bytes()
            _static_binary_mtimes[filename] = current_mtime
        return _static_binary_cache[filename]
    else:
        if filename not in _static_cache or current_mtime != _static_mtimes.get(filename):
            _static_cache[filename] = path.read_text(encoding="utf-8")
            _static_mtimes[filename] = current_mtime
        return _static_cache[filename]


def build_html() -> str:
    """Build the complete HTML dashboard from its components.

    Uses string.Template for safe substitution of CSS and JavaScript content.
    The template uses $variable syntax for placeholders.

    All files (HTML template, CSS, JS) support hot-reload: changes are
    detected automatically without server restart.

    Returns:
        Complete HTML dashboard string
    """
    return _get_template().safe_substitute(
        css=_get_static_file("css"),
        js_utils=_get_static_file("js_utils"),
        js_charts=_get_static_file("js_charts"),
        js_core=_get_static_file("js_core"),
    )
