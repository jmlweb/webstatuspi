"""Progressive Web App assets for the monitoring dashboard.

This package contains the PWA manifest, service worker, and app icons.
Icons are loaded from static files for easier maintenance.

PWA Features:
- Installable on mobile and desktop devices
- Offline support via Service Worker caching
- Cache versioning for update detection (auto-computed from dashboard content)
- Cyberpunk aesthetic matching the dashboard
"""

from ._icons import ICON_192_PNG, ICON_512_PNG
from ._manifest import MANIFEST_JSON
from ._offline import OFFLINE_BANNER_CSS, OFFLINE_BANNER_HTML
from ._registration import SW_REGISTRATION_JS
from ._service_worker import SERVICE_WORKER_JS
from ._version import PWA_VERSION

__all__ = [
    "PWA_VERSION",
    "MANIFEST_JSON",
    "SERVICE_WORKER_JS",
    "ICON_192_PNG",
    "ICON_512_PNG",
    "SW_REGISTRATION_JS",
    "OFFLINE_BANNER_CSS",
    "OFFLINE_BANNER_HTML",
]
