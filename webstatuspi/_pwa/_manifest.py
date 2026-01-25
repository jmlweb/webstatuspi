"""Web App Manifest for PWA installation.

Defines app metadata for installation on home screens.
Uses cyberpunk theme colors matching the dashboard.
"""

from ._version import PWA_VERSION

# WEB APP MANIFEST
# Defines app metadata for installation on home screens.
# Uses cyberpunk theme colors matching the dashboard.

MANIFEST_JSON = f"""{{
  "name": "WebStatusπ // SYSTEM MONITOR",
  "short_name": "WebStatusπ",
  "description": "Lightweight web monitoring dashboard for Raspberry Pi",
  "version": "{PWA_VERSION}",
  "id": "/",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "orientation": "any",
  "background_color": "#0a0a0f",
  "theme_color": "#00fff9",
  "icons": [
    {{
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any"
    }},
    {{
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "maskable"
    }},
    {{
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any"
    }},
    {{
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable"
    }}
  ],
  "shortcuts": [
    {{
      "name": "Status Overview",
      "short_name": "Status",
      "description": "View all monitored services",
      "url": "/",
      "icons": [{{ "src": "/icon-192.png", "sizes": "192x192" }}]
    }}
  ],
  "categories": ["utilities", "productivity"]
}}"""
