"""HTML dashboard for the monitoring web interface.

This package contains the embedded HTML/CSS/JS dashboard served at the root endpoint.
The dashboard is static HTML that fetches data dynamically via JavaScript from /status.

Separated into multiple modules for better maintainability while keeping zero dependencies.

The HTML template supports hot-reload: changes to dashboard.html are detected
automatically without requiring a server restart.
"""

from ._css import CSS_STYLES
from ._html import build_html
from ._js_charts import JS_CHARTS
from ._js_core import JS_CORE
from ._js_utils import JS_UTILS

# CSP nonce placeholder for runtime replacement
CSP_NONCE_PLACEHOLDER = "__CSP_NONCE__"


def get_dashboard() -> str:
    """Get the complete HTML dashboard.

    This function rebuilds the dashboard if the HTML template has changed,
    enabling hot-reload during development. The CSS and JavaScript are
    currently not hot-reloaded (require server restart).

    Returns:
        Complete HTML dashboard string with placeholders for CSP nonce
        and initial data.
    """
    return build_html(CSS_STYLES, JS_UTILS, JS_CHARTS, JS_CORE)


# For backwards compatibility, provide HTML_DASHBOARD as initial value
# Note: This won't hot-reload. Use get_dashboard() for hot-reload support.
HTML_DASHBOARD = get_dashboard()

__all__ = [
    "HTML_DASHBOARD",
    "CSP_NONCE_PLACEHOLDER",
    "get_dashboard",
]
