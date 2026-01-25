"""Offline banner CSS and HTML for dashboard.

CSS for the offline indicator banner shown when network is unavailable.
"""

# OFFLINE BANNER CSS (for dashboard HTML)
# CSS for the offline indicator banner shown when network is unavailable.

OFFLINE_BANNER_CSS = """
        /* Offline banner - hidden by default, shown when body has .offline class */
        #offlineBanner {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: linear-gradient(90deg, var(--red), #cc0033);
            color: white;
            text-align: center;
            padding: 0.5rem;
            z-index: 10000;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            font-weight: 600;
            box-shadow: 0 2px 10px rgba(255, 0, 64, 0.5);
            animation: errorFlicker 2s infinite;
        }
        body.offline #offlineBanner {
            display: block;
        }
        body.offline header {
            margin-top: 2rem;
        }
"""

# OFFLINE BANNER HTML (for dashboard HTML)
# HTML element for the offline indicator banner.

OFFLINE_BANNER_HTML = (
    """<div id="offlineBanner" role="alert" aria-live="assertive">⚠ OFFLINE MODE - Showing cached data</div>"""
)
