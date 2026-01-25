"""Service Worker JavaScript for PWA caching.

Handles caching strategy:
- Static assets (HTML, manifest): Cache-first for fast loading
- API endpoints (/status, /history): Network-first with cache fallback
- Other endpoints (/reset): Network-only (no caching for destructive ops)
"""

from ._version import PWA_VERSION

# SERVICE WORKER
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
