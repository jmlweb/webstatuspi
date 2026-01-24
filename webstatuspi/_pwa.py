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

    // API endpoints: Network-first with cache fallback
    if (url.pathname.startsWith('/status') || url.pathname.startsWith('/history')) {{
        event.respondWith(
            fetch(event.request)
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
                            return cachedResponse;
                        }}
                        // No cache, return offline fallback
                        return new Response(
                            JSON.stringify({{
                                error: 'Offline',
                                urls: [],
                                summary: {{ total: 0, up: 0, down: 0 }}
                            }}),
                            {{ headers: {{ 'Content-Type': 'application/json' }} }}
                        );
                    }});
                }})
        );
        return;
    }}

    // HTML: Network-first (always get fresh content, fallback to cache offline)
    if (url.pathname === '/') {{
        event.respondWith(
            fetch(event.request)
                .then(response => {{
                    if (response.ok) {{
                        const responseClone = response.clone();
                        caches.open(STATIC_CACHE).then(cache => {{
                            cache.put(event.request, responseClone);
                        }});
                    }}
                    return response;
                }})
                .catch(() => caches.match(event.request))
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
iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAYAAABS3GwHAAAACXBIWXMAAAsTAAALEwEAmpwYAAAF
y2lUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0w
TXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRh
LyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgNS42LWMxNDUgNzkuMTYzNDk5LCAyMDE4LzA4MDgt
MTY6MjU6NDkgICAgICAgICI+IDxyZGY6UkRGIHhtbG5zOnJkZj0iaHR0cDovL3d3dy53My5vcmcv
MTk5OS8wMi8yMi1yZGYtc3ludGF4LW5zIyI+IDxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSIi
IHhtbG5zOnhtcD0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wLyIgeG1sbnM6eG1wTU09Imh0
dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0RXZ0PSJodHRwOi8vbnMuYWRv
YmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VFdmVudCMiIHhtcDpDcmVhdG9yVG9vbD0iV2Vi
U3RhdHVzUGkiIHhtcDpDcmVhdGVEYXRlPSIyMDI0LTAxLTAxVDAwOjAwOjAwWiIgeG1wOk1vZGlm
eURhdGU9IjIwMjQtMDEtMDFUMDA6MDA6MDBaIiB4bXBNTTpJbnN0YW5jZUlEPSJ1dWlkOndlYnN0
YXR1c3BpLWljb24tMTkyIiB4bXBNTTpEb2N1bWVudElEPSJ1dWlkOndlYnN0YXR1c3BpLWljb24t
MTkyIj4gPC9yZGY6RGVzY3JpcHRpb24+IDwvcmRmOlJERj4gPC94OnhtcG1ldGE+IDw/eHBhY2tl
dCBlbmQ9InIiPz7EvHhHAAAHQUlEQVR4nO3dW3LbOBCF4U7W5v2vLLuYysQyRYIE0N0H/39VqTjW
hTj4AAK8zPM8/wHI6r/RDwCMRAAQGwFAbAQAsREAxEYAEBsBQGwEALERAMRGABAbAUBsBACxEQDE
RgAQGwFAbAQAsREAxEYAEBsBQGwEALERAMRGABAbAUBsBACxEQDERgAQGwFAbAQAsREAxEYAEBsB
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
RK5CYII=
"""

# 512x512 icon - Base64 encoded PNG
# Same design as 192x192 but larger for high-res displays
_ICON_512_BASE64 = """
iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAYAAAD0eNT6AAAACXBIWXMAAAsTAAALEwEAmpwYAAAJ
gmlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0w
TXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRh
LyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgNS42LWMxNDUgNzkuMTYzNDk5LCAyMDE4LzA4LzEz
LTE2OjQwOjIyICAgICAgICAiPiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3Jn
LzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPiA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0i
IiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtbG5zOnhtcE1NPSJo
dHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvbW0vIiB4bWxuczpzdEV2dD0iaHR0cDovL25zLmFk
b2JlLmNvbS94YXAvMS4wL3NUeXBlL1Jlc291cmNlRXZlbnQjIiB4bXA6Q3JlYXRvclRvb2w9Ildl
YlN0YXR1c1BpIiB4bXA6Q3JlYXRlRGF0ZT0iMjAyNC0wMS0wMVQwMDowMDowMFoiIHhtcDpNb2Rp
ZnlEYXRlPSIyMDI0LTAxLTAxVDAwOjAwOjAwWiIgeG1wTU06SW5zdGFuY2VJRD0idXVpZDp3ZWJz
dGF0dXNwaS1pY29uLTUxMiIgeG1wTU06RG9jdW1lbnRJRD0idXVpZDp3ZWJzdGF0dXNwaS1pY29u
LTUxMiI+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNr
ZXQgZW5kPSJyIj8+vKqvhwAAC+RJREFUeJzt3U1yFEkQQOGs9fX3v7K3WMM0DJKU1T8R72VtwKoy
Mz4i+mf+/Pnz5w+AlP47+gEAOBYBACSMAAASRgAACTMCAEiYEQBAwowAABJmBACQMCMAgIQZAQAk
zAgAIGFGAAAJMwIASJgRAEDCjAAAEmYEAJAwIwCAhBkBACTMCAAgYUYAAAkzAgBImBEAQMKMAAAi
+X/Xv7/O1f/z9f/9/mf6nxEIBIZl/u/r/+vXL7a+//rr/b/2K/1PCgR6Z+5nqfzy/3u59P/x49Lt
f+e/Lv+X3i+1XyIQ6Jx5+Vr2v3//5XLZ/Pd/f7Xf+eF/+1f6nxUIdM76/v+3S/n18u/P12/bF/Ht
P6d/3vf15b/b9a/6+3/8b/0X/34HAp0yL/+9i91+rnfb/rv88Odv/5LrZXn7b/J0GxLos3mZl+XX
U7/cLuO37/+XV+H97+vt78zL5fLy533/WMa/tv+J/1oCgU6Zl8v8+v//fZ+u7fvb93+fF/vD9wz2
GwkE4vv+f738XYIvsvcnOLwAAABFSURBVN4v9OXyX//vy+3yYxm//H75v7b/Cf/aAoFumZfL5f+W
/K+/ulr6v47+b/X376+v/76u+4+f/5L/2n7d/xoBwKz82+V+ub68/J5f93+87b/Y/v/+49/dP/7/
+X3dx4mXFgiE0PdlvP19/+/f/d9yf30FL//n9X/bwF+/f+2T/n+s/YYCP4gYE4ilfP8bF7x/l5/z
dF8TgUBIfH9YbP19t9/xdR+yJgKBQ/ndv3xd2pf/8f57bv/1+p//3va3b/3f9e/+0j+uQKB75uWy
/LP8l3/53r/c/uv3/+f2/97/+//7X/7n/J/X/xHqPmRNBAKBsHN/B/j9S7L3f/f7f77/l9v/fv/3
9e+2/+y/5ff9ewQCgcDovP1t17/tP3fb/7/7P7f/93bpv/S/87/XoHuXLhCIj8y/XO7/2/3L/9+X
/+X339d/f/c+3b7n7Z+3//v7//t/f/tPDAR6Zm5L+eVl+We5/y7p5dK//Hb799+/L/T77+f7f/93
f7cO4CVa9p6BQGA4fn+JrvuHwv7vfb787b++/rn+udv/ev93u/17t/9nf99f95/YD/ASvWsgEBiO
3xf573/e/9fL738/t/99+2e3/3377/+yv+772/c/3wfdtgQCfTO/Lvn7f38v7/0s8/f/a/v39X+7
/f+3f277v3b7G/57/+df9kPl/00EAuMw/3bJbv/e7X+9/M/L/3o5v/33b//+7c/bv3d7/O/v/5f/
37/v/17/iwgE4mK5LuN/u5S3S/m+rO/f8323/3q5e7X/HKV++Xv2n8/u+9+5/nf++wgEhue+nF9+
frl9yW7/df+3//7uf7v/9+1fu++HBv/uXwIEBoP1fVlf/9n1n7/8cP++LNd/+b/8d/d/f/t53/7+
5d/nq/u1/iIwDuZ//ny7jF//7P39f/9f/yWX7u3fuP/97f97+y/+0p+3/39/wQE4CbDJWCDdz+33
9vv/8bPL5fZ57v9tv+733f/X7f/v7b/f///t79oP9VLSP9tAoCvm7/f8/yX59Wf5b/vz9c+//rf/
6/5v33/+9n///n3c/8//e/+P/o7/WgKBcHhf7vdl/PYvvv7T7d//t79u/93b3/u3v+v+/+7+77L8
b/99+7/uv9b9v0v/cAMBnAD4ykJ/X8b3P2//3P9/t//u99+3v/d9Sf/+X/t/3/+2+/+6/38P+KEH
Aqj8/v/d/t91Wb//+d2/cfvx/7r9n/fv+7/v/f8/u/+/+98YEvizDQTCYF3+V//P2//77u/bf/3+
T7/+d7v/vf3b/3u7/3u9/xPo/+f9/3sHAQJBsH7f8/+/+/bf/773P/+6/be35d9/n3r7t/93/+9f
/l/u/38+vX+AgcCwfP/D//2/t39/+zP+9pe//dv3P+v7f97/b/+/7/+J/5//3oFA7Hxflvfl/b9/
bv+r7b/bv/uf8/3v3P7f7X8Z/vd+v/gDDgQC4+u/fL/9+/bf77/v/u/+/XL/b7p9//97+f/f2/+7
/J//t/5xBgKD8e8/++/3/3a73f6/3/93+3e//9u//9+X//r9v++///r+H/c/y0CgrH//8//+3//+
e7f/e//91+/9d7n/7+3///bP+u///J/13+8g8CMOBMbh/8u++9/t/2r/39v/uvx3vy/z/+7//f77
f+v///37z+Ff9SMJBEJgvv/8f/d/9z/v9n/d/63/3+1/u/+377+d/+J/yX+9gUBcrH/+7//19r/e
/t32u/+3277/9F///33/X57/u/0fLxD4iQQCcfD+33//+7/f/27/4+1f3f7n/d/+X+u/9J/t/8k9
A4HB+O/+/+3+/9+vt/9vt9+v/+e//z++/49/E4HAqLz8+Xr/7/7z/e++/+/+7/7f7f/c/77f/+n+
P/f/s/uHGgh0z7ws17++/73t37u/v/uf+/+8/b+W//u+/+P3f8p/7YHAD/b7f+6X9X/f/t/u/2X7
/+72P/f/v/t/9z/n/3r/D/R/B4FAWMzL///t/97/z+3yf/t/bv/d3//59v/6/u/t/1+/f+B+v4FA
oGv++/J/6/7f+/93++vfv/+7///t/+3+v/v/7v8f7v++B/iyA4FB+P+y+/+v+3+7/5e3//X7//L/
d/v/c/+/6v8O9d8lEOiV+f8v+0/a/3v7X+/+3/a/7n/d/67/z///6f7f9qADgVj4+t/+v/f/d/v/
d/t/d///t/9/7//f+/9z/T/Vf8GBwCB8/S/+0/b/Xv7+/u+//P9u/+Ptf97/Y/1/sv+qA4GB+Ppy
/T9t/+fv/+/tf9z+y/v/ev+/7f/f7v8p/l8nEOiV5f7/9O//+/5/vP2P2//9+3/bf3/+b/X/6f7r
DwTCYHl7+z/b/7/b//bPd/d/u/7v23+7/4P3/yT/VQcCQ/D+L/53+3/77/t/t/11/6+3+/v+5/d/
Yf/n7f8agoGYDJaVFoN///3v/f9u/+/2P+73/+7/f+r/1/0fvP+T/FcdCAzB8vZn7P5f7v/v/p/t
f9zuz+1/u/+3/T/a/+X6/1X/tQcCgbHc/u+//V/3//b3/f/e/vv7f9v/d/0ftv/b/zcMBGJhWVba
/y8u/+f+P/d/7P77/vf8/9X+z/Vf9F90IDAI3/+y/3/b/377L//X/d/uv+7///bf23/1f/v+j9v/
K/8PBAKI5O/L/3Lpv/7n/3/bf7n/3/u//b3b/9f9/+n+b+z/J//1BwIx8PJnuf/n9v9z/7/3//7v
X/f/tv+37//P/0//P9F/9YFATCz3//z5c/+/b/+//r89/v79/+/v/87/v93/bfvf+i8wEBiF5e3P
2P1/v/3f+3/73/V/v/5L///S/pP/ugOBkXj78/71zy/+/e1f2f+/t/+2/f+o//f2H9F/BoEAOBCo
iUWRrHNf/+/u/93+3+X+/9L/of7b9p/mPygQaJvl7u8v7f+8+5f7+//c/9v/d/+/y/25/sf+cw0E
4mP54f/L/9/tf97/y/1/7v+/vv/d/m/Z/6f/9AwEKuPfe27/9/Z/bv/9/t/b/7p+6P7b9v+a/eMI
BAJjef3z9v/r/t/b/3x93f+/t/+p/of7/+//BQUCbbEs/3n7/7r/9+e/3v7f7c/9v+1/vf+H7v+y
//9gIBAHy+ufr5f//3b/7+1/bv+9/bft/5D+j+g/10CgNpa3P2P3f2n/Z/sv9//U/sf2/8P+awsE
umJZfn/733r5/+v+397/6/1/6D///m/sfxJ8oFwgCpan/3Z7/+/t//z6d/f/tf2f+v/w/U//FxAI
xMDydr+X5b/b/v91/2/b/1n+H9t/Yv/5BgI9sdzuP/6c3f/l9u/T/4ftf7n/B/s/8V9EIDAI8/av
t/9y+8v/9f//d/9/av9j+z9k/0cRCMTD8nK/l+V/v/+P7f96/8fuf2z/rf0n///H9p9vINALy+3+
sv2/t//y/3X/f3j/4/3f8n9OgUAQLO/3e1mW+/1l+3+5/6f1/5Ltv77/8/6LCQTaZbn/f9v+t+3/
8u3+X/d/9P6H7D/I/6H/mQQCHTHfLv/l7u9f/+97+3/6/7H75/d/xv5/3H/ugUAULK/3e/kv/+X7
yyW6++f+j+8/Zf9R/E/6bycQiIHl7c/Y/V/7P7f/8vaX5X/c/ub+J/af8F9xINAm8+3+sv2//d/t
/6T9f/r/a/bv/U8kEAiA5e1+f/7P2/2/t/9z//v3f3T/I/rP8198INAty9v9Xpbl/8fb/9j/8f33
9/+h/pP/CwsE2mG+/f+2/1/u9/f7b/vft/9y+6/+D+7/2P0//r+sQKAX5tufz//5tz//dP9X/g/b
/2/7/wL/CQYC3bC83e/lfv+X/99+/B/3/6/9f9P+I/nPOxBoj+X25+3+3/a/3v/X9t+X//79H73/
8P7z/CccCLTJ/Hr/l+U/3f7l/n/qf8D+k/unGQj0wHy7/5/X+3/7/+76n/T/7/u/tP8c/4kHAm2w
3O5/v/9t/7fbX/7n/v/9/l+7/+/u/4z9f8l/BoFAD8zLH7/9l/v/uv9t+5/s/+D9h/afz38VgUB7
LPf7Xf7b7X/c/7r/J/sf3n9+/zn+qw8E2mC53f96+y+3/+37bfvf3P/w/c/3n8d/LYFA+yzL/f9j
/9/+vb//E/Y/ev+R/ef83zUQaI35dv/l7f/c//b7b/tf7v+u+z9q/w/8ZxUI9MByv//l//fy/23/
a/tvb/999P4H7D+y/7z/dQcCbbDc/r/u/+X2X+7/avsfs/8c/hP/xQcCLTIv9/+/3v/19u/2v+7/
7v0/ef8f8J/of+SBQA/Mt/9/v/+3/37/W/tv2/+9/vfyH+S/gkCgH5bb/e+3f/t/u/0r/Y/Z/4f8
F/rPKBDogfn2/+X+3+5/v/+1/XfZ/9D9P8N/BoFAGyy3/7+7/7f9d/v/tv2f+v96/0/0n2Ig0C7z
cr/9l/91+z/d/5T9B++/wH8egUBbLLf/b/d/+3+3/Y/v/xX7P+g/40AgDub79t/u/+v9T/Sf+J/N
f6GBQD/My/1f7/9t/9P2f9P+8/qv/q8gEOiJ+fa/7f9t/9P2/57/bP4rDATaZ17u/+X+X29/Tf/D
/pfxn/Of3H/CgUBbLPf7L7f/a/t/d///3n/p/y7+OwwE2mJ5+X/b/937v2n/H/df6z+y/0ICgQ5Z
bn++3v6l/w/c/9L/G/g/7L++QKBd5tu/cvuX/l97/y/Y/y//Cf+FBgJdMi93/+X+//P9z+//I/cP
/k8vEGib5f6/3v4v9/+a/S/9/+D/mgKBtljuf96X/2P2/+H9P+B/woFAu8y3/7ftL/1/+P7z+q85
EOia5fb/v+X+j9r/H/ef/J9kINAO83K/3e5/ufz/9P4/5j/xQKB9lrf/z+2//X+7/V/cf/6BQNvM
y/+3/V+7/+v2/6H/Cf7LDATC4Ptt/3K//X/b/uL+h/ef+i89EOiC5e7/bfsv/d/V/6fv/+j+xf/V
BAJtstz93/a/bv/r+/+I/tv0X+8/m0CgPea7/93+r/df+3+K//r+6/3XFwi0y3K7/9r/6++/Zv/f
/L+i/woDgbZYbn/e/r/dftv+c/5X/F/xP71AoG2W5e7/dvu/bP9L+2/R/5D/ugKBvlhu/9fuf33/
5f4v+5/Wf93/LAOBEFCZ5EBwAoAEEQBAwggAIGFGAAAJMwIASJgRAEDCjAAAEmYEAJAwIwCAhBkB
ACTMCAAgYUYAAAkzAgBImBEAQMKMAAAi+T/U9sOQIEy7tQAAAABJRU5ErkJggg==
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
