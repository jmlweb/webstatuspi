"""HTML dashboard for the monitoring web interface.

This package contains the embedded HTML/CSS/JS dashboard served at the root endpoint.
The dashboard is static HTML that fetches data dynamically via JavaScript from /status.

The CSS and JavaScript are stored as native files in the static/ directory and
inlined into the HTML at runtime for a single self-contained response.

All files support hot-reload: changes to dashboard.html, styles.css, and JS files
are detected automatically without requiring a server restart.
"""

from ._html import build_html

# CSP nonce placeholder for runtime replacement
CSP_NONCE_PLACEHOLDER = "__CSP_NONCE__"


def get_dashboard() -> str:
    """Get the complete HTML dashboard.

    This function rebuilds the dashboard if any source files have changed,
    enabling hot-reload during development. The HTML template, CSS, and
    JavaScript files are all monitored for changes.

    Returns:
        Complete HTML dashboard string with placeholders for CSP nonce
        and initial data.
    """
    return build_html()


# For backwards compatibility, provide HTML_DASHBOARD as initial value
# Note: This won't hot-reload. Use get_dashboard() for hot-reload support.
HTML_DASHBOARD = get_dashboard()

__all__ = [
    "HTML_DASHBOARD",
    "CSP_NONCE_PLACEHOLDER",
    "get_dashboard",
]
