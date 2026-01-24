"""HTML template for the dashboard.

This module loads the HTML template from dashboard.html and provides
a function to build the complete HTML by substituting CSS and JavaScript.

The template is automatically reloaded when the file changes (hot-reload).
"""

from pathlib import Path
from string import Template

_TEMPLATE_PATH = Path(__file__).parent / "dashboard.html"

# Cache for template and its mtime
_template_cache: Template | None = None
_template_mtime: float = 0.0


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


def build_html(css: str, js_utils: str, js_charts: str, js_core: str) -> str:
    """Build the complete HTML dashboard from its components.

    Uses string.Template for safe substitution of CSS and JavaScript content.
    The template uses $variable syntax for placeholders.

    The HTML template is automatically reloaded if the file changes,
    enabling hot-reload during development without server restart.

    Args:
        css: CSS styles string
        js_utils: JavaScript utility functions string
        js_charts: JavaScript chart functions string
        js_core: JavaScript core functionality string

    Returns:
        Complete HTML dashboard string
    """
    return _get_template().safe_substitute(
        css=css,
        js_utils=js_utils,
        js_charts=js_charts,
        js_core=js_core,
    )
