"""HTML dashboard for the monitoring web interface.

This package contains the embedded HTML/CSS/JS dashboard served at the root endpoint.
The dashboard is static HTML that fetches data dynamically via JavaScript from /status.

Separated into multiple modules for better maintainability while keeping zero dependencies.
"""

from ._css import CSS_STYLES
from ._html import build_html
from ._js_charts import JS_CHARTS
from ._js_core import JS_CORE
from ._js_utils import JS_UTILS

# Assemble the complete HTML dashboard
HTML_DASHBOARD = build_html(CSS_STYLES, JS_UTILS, JS_CHARTS, JS_CORE)

# Split HTML at the initial data marker for efficient concatenation
# This avoids creating a new 35KB+ string on every request
_HTML_PARTS = HTML_DASHBOARD.split("__INITIAL_DATA__")
HTML_DASHBOARD_PREFIX = _HTML_PARTS[0].encode("utf-8")
HTML_DASHBOARD_SUFFIX = _HTML_PARTS[1].encode("utf-8")

# CSP nonce placeholder for runtime replacement
CSP_NONCE_PLACEHOLDER = "__CSP_NONCE__"

__all__ = [
    "HTML_DASHBOARD",
    "HTML_DASHBOARD_PREFIX",
    "HTML_DASHBOARD_SUFFIX",
    "CSP_NONCE_PLACEHOLDER",
]
