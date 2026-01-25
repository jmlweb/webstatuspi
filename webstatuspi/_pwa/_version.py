"""PWA version computation.

This module computes the PWA version from dashboard content hash,
ensuring automatic cache invalidation when dashboard changes.
"""

import hashlib

from .._dashboard import HTML_DASHBOARD


def _compute_pwa_version() -> str:
    """Compute PWA version from dashboard content hash.

    This ensures the service worker cache is automatically invalidated
    whenever the dashboard HTML/CSS/JS changes, without manual version bumps.
    """
    content_hash = hashlib.sha256(HTML_DASHBOARD.encode()).hexdigest()[:8]
    return f"1.0.{content_hash}"


# PWA VERSION - Auto-computed from dashboard content hash
# This version is embedded in both manifest and service worker.
# Changes to _dashboard.py automatically update this version.
PWA_VERSION = _compute_pwa_version()
