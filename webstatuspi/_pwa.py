"""Progressive Web App assets for the monitoring dashboard.

This module contains the PWA manifest, service worker, and app icons.
All assets are embedded as string/bytes constants for zero-dependency deployment.

PWA Features:
- Installable on mobile and desktop devices
- Offline support via Service Worker caching
- Cache versioning for update detection (auto-computed from dashboard content)
- Cyberpunk aesthetic matching the dashboard
"""

import base64
import hashlib

from ._dashboard import HTML_DASHBOARD


def _compute_pwa_version() -> str:
    """Compute PWA version from dashboard content hash.

    This ensures the service worker cache is automatically invalidated
    whenever the dashboard HTML/CSS/JS changes, without manual version bumps.
    """
    content_hash = hashlib.sha256(HTML_DASHBOARD.encode()).hexdigest()[:8]
    return f"1.0.{content_hash}"


# =============================================================================
# PWA VERSION - Auto-computed from dashboard content hash
# =============================================================================
# This version is embedded in both manifest and service worker.
# Changes to _dashboard.py automatically update this version.
PWA_VERSION = _compute_pwa_version()

# =============================================================================
# WEB APP MANIFEST
# =============================================================================
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

# =============================================================================
# SERVICE WORKER
# =============================================================================
# Handles caching strategy:
# - Static assets (HTML, manifest): Cache-first for fast loading
# - API endpoints (/status, /history): Network-first with cache fallback
# - Other endpoints (/reset): Network-only (no caching for destructive ops)

SERVICE_WORKER_JS = f"""// Service Worker for WebStatusπ PWA
// Version: {PWA_VERSION} - Auto-computed from dashboard content hash

const SW_VERSION = '{PWA_VERSION}';
const CACHE_NAME = `webstatuspi-v${{SW_VERSION}}`;
const STATIC_CACHE = `webstatuspi-static-v${{SW_VERSION}}`;
const API_CACHE = `webstatuspi-api-v${{SW_VERSION}}`;

// Assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/manifest.json',
    '/icon-192.png',
    '/icon-512.png'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {{
    console.log('[SW] Installing version', SW_VERSION);
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {{
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            }})
            .then(() => self.skipWaiting())
    );
}});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {{
    console.log('[SW] Activating version', SW_VERSION);
    event.waitUntil(
        caches.keys().then(cacheNames => {{
            return Promise.all(
                cacheNames
                    .filter(cacheName => {{
                        return cacheName.startsWith('webstatuspi-') &&
                               !cacheName.includes(`v${{SW_VERSION}}`);
                    }})
                    .map(cacheName => {{
                        console.log('[SW] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }})
            );
        }})
        .then(() => self.clients.claim())
    );
}});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {{
    const url = new URL(event.request.url);

    // Skip non-GET requests
    if (event.request.method !== 'GET') {{
        return;
    }}

    // Skip external requests (different origin) - let browser handle them directly
    if (url.origin !== self.location.origin) {{
        return;
    }}

    // API endpoints: Network-first with cache fallback and fast timeout
    // Short timeout (3s) to quickly detect server restart and show cached data
    if (url.pathname.startsWith('/status') || url.pathname.startsWith('/history')) {{
        event.respondWith(
            fetch(event.request, {{
                signal: AbortSignal.timeout(3000)
            }})
                .then(response => {{
                    if (response.ok) {{
                        const responseClone = response.clone();
                        caches.open(API_CACHE).then(cache => {{
                            cache.put(event.request, responseClone);
                        }});
                    }}
                    return response;
                }})
                .catch(() => {{
                    return caches.match(event.request).then(cachedResponse => {{
                        if (cachedResponse) {{
                            // Add header to indicate this is cached data
                            const headers = new Headers(cachedResponse.headers);
                            headers.set('X-From-Cache', 'true');
                            return new Response(cachedResponse.body, {{
                                status: cachedResponse.status,
                                statusText: cachedResponse.statusText,
                                headers
                            }});
                        }}
                        // No cache, return offline fallback
                        return new Response(
                            JSON.stringify({{
                                error: 'Offline',
                                urls: [],
                                summary: {{ total: 0, up: 0, down: 0 }}
                            }}),
                            {{ headers: {{ 'Content-Type': 'application/json', 'X-From-Cache': 'true' }} }}
                        );
                    }});
                }})
        );
        return;
    }}

    // HTML: Stale-While-Revalidate (serve cache instantly, update in background)
    // This prevents 502 errors during server restarts - cached HTML loads immediately
    // while the background fetch silently fails or updates the cache
    if (url.pathname === '/') {{
        event.respondWith(
            caches.match(event.request).then(cachedResponse => {{
                // Start background fetch to update cache (don't await)
                const fetchPromise = fetch(event.request, {{
                    // Short timeout to detect server down quickly
                    signal: AbortSignal.timeout(5000)
                }})
                    .then(response => {{
                        if (response.ok) {{
                            const responseClone = response.clone();
                            caches.open(STATIC_CACHE).then(cache => {{
                                cache.put(event.request, responseClone);
                            }});
                        }}
                        return response;
                    }})
                    .catch(() => null); // Silently ignore fetch errors

                // Return cached response immediately if available
                if (cachedResponse) {{
                    return cachedResponse;
                }}
                // No cache: wait for network (first visit)
                return fetchPromise.then(response => {{
                    if (response) return response;
                    // Network failed and no cache - show offline page
                    return new Response(
                        `<!DOCTYPE html><html><head><meta charset="utf-8"><title>WebStatusπ - Offline</title>
                        <style>body{{background:#0a0a0f;color:#00fff9;font-family:monospace;display:flex;
                        justify-content:center;align-items:center;height:100vh;margin:0}}
                        div{{text-align:center}}h1{{font-size:3em}}p{{opacity:0.7}}</style></head>
                        <body><div><h1>⚡ OFFLINE</h1><p>Server is restarting...<br>This page will auto-refresh.</p>
                        <script>setTimeout(()=>location.reload(),3000)</script></div></body></html>`,
                        {{ headers: {{ 'Content-Type': 'text/html' }} }}
                    );
                }});
            }})
        );
        return;
    }}

    // Static assets: Cache-first (icons, manifest)
    if (url.pathname === '/manifest.json' ||
        url.pathname.startsWith('/icon-')) {{
        event.respondWith(
            caches.match(event.request)
                .then(cachedResponse => {{
                    if (cachedResponse) {{
                        return cachedResponse;
                    }}
                    return fetch(event.request).then(response => {{
                        if (response.ok) {{
                            const responseClone = response.clone();
                            caches.open(STATIC_CACHE).then(cache => {{
                                cache.put(event.request, responseClone);
                            }});
                        }}
                        return response;
                    }});
                }})
        );
        return;
    }}

    // Default: Network-only (for /reset, /health, etc.)
    event.respondWith(fetch(event.request));
}});

// Handle messages from clients
self.addEventListener('message', (event) => {{
    if (event.data && event.data.type === 'SKIP_WAITING') {{
        self.skipWaiting();
    }}
}});
"""

# =============================================================================
# APP ICONS
# =============================================================================
# Cyberpunk-styled icons with cyan accent on dark background.
# Generated as minimal PNG files with geometric design.
# Icons are stored as base64-encoded bytes for embedding.

# 192x192 icon - Base64 encoded PNG
# Design: Dark background (#0a0a0f) with cyan (#00fff9) geometric pattern
# representing a monitoring/status indicator with a diamond shape
_ICON_192_BASE64 = """
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
"""

# 512x512 icon - Base64 encoded PNG
# Same design as 192x192 but larger for high-res displays
_ICON_512_BASE64 = """
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4XBW/hKBrwESUdU8mjhs0nim/4c/zEBxwUlIi/RK1jKLVJEPylDN7NjQsWTl79NPnyHXb+zMyl8iBgAiqopP/xtAN2uyCEAxLFwP2Gnl/FrJm3w8MQrpUalee+tCEWhW/hIxABBRFT2GCDKeAIAaELIACL9M1RGLsj3850gEsfVIr7FAvv12B/n92l5GSa7+iRgAiKiqCoURADR+2v131Lf98n0VD9hZZKNOVDpPPXshK3+JWAZERKjSmwAwrr0Tlr3TSGGXqe33l4MAI8IwFLH48bzxEzEAEFHVfxOg7K/8/18kXzoiArcAiOgweBvAHOBX9ZgAiBgAiOjweBSQR/URgQcBEREREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERExAPBbQERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERExADAbwEREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABERETEAEBEREQMAERERMQAQERERAwAREREDABERETEAEBEREQMAERERMQAQERERAwARERExABAREREDABEREVUl/w8mENsqHsfeVwAAAABJRU5ErkJggg==
"""

# Decode icons to bytes
ICON_192_PNG = base64.b64decode(_ICON_192_BASE64.replace("\n", ""))
ICON_512_PNG = base64.b64decode(_ICON_512_BASE64.replace("\n", ""))

# =============================================================================
# SERVICE WORKER REGISTRATION CODE (for dashboard HTML)
# =============================================================================
# This JavaScript snippet should be added to the dashboard HTML to register
# the service worker and handle updates.

SW_REGISTRATION_JS = """
        // ========================================
        // PWA: Service Worker Registration
        // ========================================
        if ('serviceWorker' in navigator) {
            // Auto-refresh when a new SW takes control
            let refreshing = false;
            navigator.serviceWorker.addEventListener('controllerchange', () => {
                if (refreshing) return;
                refreshing = true;
                console.log('[PWA] New version activated, refreshing...');
                window.location.reload();
            });

            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/sw.js')
                    .then(registration => {
                        console.log('[PWA] Service Worker registered');

                        // Check for updates every 60 seconds
                        setInterval(() => {
                            registration.update();
                        }, 60000);

                        // Handle updates - trigger skipWaiting on new SW
                        registration.addEventListener('updatefound', () => {
                            const newWorker = registration.installing;
                            newWorker.addEventListener('statechange', () => {
                                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                    console.log('[PWA] New version installed, activating...');
                                    newWorker.postMessage({ type: 'SKIP_WAITING' });
                                }
                            });
                        });
                    })
                    .catch(error => {
                        console.error('[PWA] Service Worker registration failed:', error);
                    });
            });
        }

        // ========================================
        // PWA: Online/Offline Detection (uses CSS class, no inline styles due to CSP)
        // ========================================
        function updateOnlineStatus() {
            if (navigator.onLine) {
                document.body.classList.remove('offline');
                // Refresh data when coming back online
                fetchStatus();
            } else {
                document.body.classList.add('offline');
            }
        }

        window.addEventListener('online', updateOnlineStatus);
        window.addEventListener('offline', updateOnlineStatus);

        // Check initial status
        if (!navigator.onLine) {
            updateOnlineStatus();
        }
"""

# =============================================================================
# OFFLINE BANNER CSS (for dashboard HTML)
# =============================================================================
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

# =============================================================================
# OFFLINE BANNER HTML (for dashboard HTML)
# =============================================================================
# HTML element for the offline indicator banner.

OFFLINE_BANNER_HTML = (
    """<div id="offlineBanner" role="alert" aria-live="assertive">⚠ OFFLINE MODE - Showing cached data</div>"""
)
