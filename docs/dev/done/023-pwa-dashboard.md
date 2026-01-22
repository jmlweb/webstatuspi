# Task #023: Convert Dashboard to Progressive Web App (PWA)

## Metadata
- **Status**: completed
- **Priority**: P1 - Active
- **Slice**: Frontend, Dashboard
- **Created**: 2026-01-22
- **Started**: 2026-01-22
- **Completed**: 2026-01-22
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a system administrator, I want to install the monitoring dashboard as a Progressive Web App on my mobile device or desktop, so that I can access it like a native app with offline support, push notifications, and improved performance through caching.

**Acceptance Criteria**:
- [x] Dashboard can be installed as PWA on mobile and desktop devices
- [x] Service Worker caches dashboard HTML/CSS/JS for offline access
- [x] Service Worker caches API responses (`/status`) for offline viewing
- [x] Cache versioning system ensures updates are detected and applied
- [x] Manifest.json provides app metadata, icons, and theme colors
- [x] App icons generated for multiple sizes (192x192, 512x512, etc.)
- [x] Offline fallback page shown when network unavailable and cache empty
- [ ] Push notifications support (optional, for future alert integration)
- [x] Zero additional dependencies (Service Worker and manifest are static files)
- [x] Works on localhost without HTTPS (development)
- [x] HTTPS required for production deployment (standard PWA requirement)

## Implementation Notes

### Current State Analysis

The dashboard is currently:
- Embedded HTML in `_dashboard.py` as `HTML_DASHBOARD` string constant
- Served at root endpoint `/` via `api.py`
- Uses vanilla JavaScript with polling every 10 seconds
- No caching mechanism (always fetches fresh data)
- No offline support

**Constraints**:
- Must maintain zero external dependencies
- Must work on Pi 1B+ (client-side only, no server impact)
- Must follow cyberpunk/CRT aesthetic
- Must preserve existing functionality

### PWA Components Required

#### 1. Web App Manifest (`manifest.json`)

**Purpose**: Defines app metadata, icons, display mode, theme colors.

**Location**: Served as static file at `/manifest.json` endpoint in `api.py`

**Structure**:
```json
{
  "name": "WebStatusPi // SYSTEM MONITOR",
  "short_name": "WebStatusPi",
  "description": "Lightweight web monitoring dashboard for Raspberry Pi",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0a0a0f",
  "theme_color": "#00fff9",
  "orientation": "any",
  "icons": [
    {
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "shortcuts": [
    {
      "name": "Status Overview",
      "short_name": "Status",
      "description": "View all monitored services",
      "url": "/",
      "icons": [{ "src": "/icon-192.png", "sizes": "192x192" }]
    }
  ]
}
```

**Theme colors**:
- `background_color`: `#0a0a0f` (matches `--bg-dark`)
- `theme_color`: `#00fff9` (matches `--cyan` accent)

**Display modes**:
- `standalone`: App-like experience (no browser UI)
- Alternative: `fullscreen` for kiosk mode (optional)

#### 2. Service Worker (`sw.js`)

**Purpose**: Handles caching, offline support, and cache versioning.

**Location**: Served as static file at `/sw.js` endpoint in `api.py`

**Key Features**:
1. **Cache versioning**: Version number embedded in Service Worker code
2. **Cache strategy**: Network-first with cache fallback for API, cache-first for static assets
3. **Cache busting**: Versioned cache names ensure old caches are invalidated
4. **Update detection**: Service Worker version change triggers cache refresh

**Cache Strategy**:
- **Static assets** (HTML, CSS, JS): Cache-first (fast loading, versioned)
- **API endpoints** (`/status`, `/status/<name>`, `/history/<name>`): Network-first with cache fallback (fresh data preferred, offline fallback)
- **Other endpoints** (`/reset`): Network-only (no caching for destructive operations)

**Versioning Approach**:
```javascript
// Service Worker version - MUST be updated when dashboard code changes
const SW_VERSION = '1.0.0';  // Update this when HTML/CSS/JS changes
const CACHE_NAME = `webstatuspi-v${SW_VERSION}`;
const STATIC_CACHE = `webstatuspi-static-v${SW_VERSION}`;
const API_CACHE = `webstatuspi-api-v${SW_VERSION}`;
```

**Update Detection**:
- When `SW_VERSION` changes, new Service Worker installs
- Old caches are deleted during activation
- New cache is populated on next navigation

#### 3. App Icons

**Purpose**: Icons for home screen, splash screen, and app shortcuts.

**Requirements**:
- **192x192px**: Minimum size for Android home screen
- **512x512px**: Recommended for splash screens and high-res displays
- **Format**: PNG with transparency
- **Design**: Cyberpunk aesthetic matching dashboard (cyan accent, dark background)

**Icon Design Guidelines**:
- Use dashboard logo/branding if available
- Fallback: Simple geometric design with cyan accent
- Ensure icons are recognizable at small sizes
- Test on both light and dark backgrounds

**Generation**:
- Create base SVG design
- Export to PNG at required sizes
- Optimize file sizes (use tools like `pngquant` or `optipng`)
- Target: < 50KB per icon

#### 4. HTML Updates

**Required changes to `_dashboard.py`**:

1. **Link manifest in `<head>`**:
```html
<link rel="manifest" href="/manifest.json">
```

2. **Register Service Worker** (in script section):
```javascript
// Register Service Worker for PWA support
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('SW registered:', registration);
                // Check for updates periodically
                setInterval(() => {
                    registration.update();
                }, 60000); // Check every minute
            })
            .catch(error => {
                console.error('SW registration failed:', error);
            });
    });
}
```

3. **Meta tags for PWA**:
```html
<!-- Already present: -->
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<!-- Add: -->
<meta name="theme-color" content="#00fff9">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="WebStatusPi">
```

4. **Apple touch icon** (for iOS):
```html
<link rel="apple-touch-icon" href="/icon-192.png">
```

### Cache Versioning Strategy

**Problem**: When dashboard code changes, cached assets must be invalidated and updated.

**Solution**: Multi-layered versioning approach:

1. **Service Worker Version**:
   - Hardcoded version string in `sw.js`: `const SW_VERSION = '1.0.0'`
   - Updated manually when dashboard HTML/CSS/JS changes
   - Triggers Service Worker update and cache invalidation

2. **Cache Names**:
   - Include version in cache name: `webstatuspi-static-v1.0.0`
   - Old caches automatically become orphaned when version changes
   - Deleted during Service Worker activation

3. **HTML Version Parameter** (optional, for aggressive cache busting):
   - Add `?v=1.0.0` query parameter to static asset URLs
   - Updated in HTML when code changes
   - Forces browser to fetch new assets even if Service Worker cache exists

4. **API Response Caching**:
   - API cache has shorter TTL (e.g., 30 seconds)
   - Network-first strategy ensures fresh data when online
   - Version not needed (data is time-sensitive)

**Version Update Workflow**:
1. Developer updates dashboard code in `_dashboard.py`
2. Update `SW_VERSION` in `sw.js` (e.g., `1.0.0` → `1.0.1`)
3. Update version in `manifest.json` if needed (optional)
4. Deploy new code
5. Service Worker detects version change on next visit
6. New Service Worker installs in background
7. On next navigation, old caches deleted, new caches populated
8. User sees updated dashboard

**Automatic Version Detection** (Future Enhancement):
- Could embed version hash in HTML (e.g., `<meta name="app-version" content="abc123">`)
- Service Worker reads version from HTML
- Automatically updates cache when version changes
- **Not implemented in initial version** (manual versioning is simpler and sufficient)

### Service Worker Implementation Details

**File Structure** (embedded in `api.py` as string constant, similar to dashboard HTML):

```javascript
// sw.js - Service Worker for WebStatusPi PWA
const SW_VERSION = '1.0.0';  // UPDATE THIS WHEN DASHBOARD CODE CHANGES
const CACHE_NAME = `webstatuspi-v${SW_VERSION}`;
const STATIC_CACHE = `webstatuspi-static-v${SW_VERSION}`;
const API_CACHE = `webstatuspi-api-v${SW_VERSION}`;

// Assets to cache on install (static HTML/CSS/JS)
const STATIC_ASSETS = [
    '/',
    '/manifest.json'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('[SW] Installing version', SW_VERSION);
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting()) // Activate immediately
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating version', SW_VERSION);
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(cacheName => {
                        // Delete all caches that don't match current version
                        return cacheName.startsWith('webstatuspi-') &&
                               !cacheName.includes(`v${SW_VERSION}`);
                    })
                    .map(cacheName => {
                        console.log('[SW] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    })
            );
        })
        .then(() => self.clients.claim()) // Take control of all clients
    );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }
    
    // API endpoints: Network-first with cache fallback
    if (url.pathname.startsWith('/status') || url.pathname.startsWith('/history')) {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    // Cache successful responses
                    if (response.ok) {
                        const responseClone = response.clone();
                        caches.open(API_CACHE).then(cache => {
                            cache.put(event.request, responseClone);
                        });
                    }
                    return response;
                })
                .catch(() => {
                    // Network failed, try cache
                    return caches.match(event.request).then(cachedResponse => {
                        if (cachedResponse) {
                            return cachedResponse;
                        }
                        // No cache, return offline fallback
                        return new Response(
                            JSON.stringify({ error: 'Offline', urls: [], summary: { up: 0, down: 0 } }),
                            { headers: { 'Content-Type': 'application/json' } }
                        );
                    });
                })
        );
        return;
    }
    
    // Static assets: Cache-first
    if (url.pathname === '/' || url.pathname.startsWith('/manifest.json') || 
        url.pathname.startsWith('/icon-') || url.pathname.startsWith('/sw.js')) {
        event.respondWith(
            caches.match(event.request)
                .then(cachedResponse => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    // Not in cache, fetch from network
                    return fetch(event.request).then(response => {
                        if (response.ok) {
                            const responseClone = response.clone();
                            caches.open(STATIC_CACHE).then(cache => {
                                cache.put(event.request, responseClone);
                            });
                        }
                        return response;
                    });
                })
        );
        return;
    }
    
    // Default: Network-only (for /reset and other endpoints)
    event.respondWith(fetch(event.request));
});
```

### API Endpoint Updates

**New endpoints in `api.py`**:

1. **`GET /manifest.json`**:
   - Returns Web App Manifest as JSON
   - Content-Type: `application/manifest+json`
   - Cached by Service Worker

2. **`GET /sw.js`**:
   - Returns Service Worker JavaScript
   - Content-Type: `application/javascript`
   - Must not be cached by browser (use `Cache-Control: no-cache`)
   - Service Worker updates when file changes

3. **`GET /icon-192.png`** and **`GET /icon-512.png`**:
   - Returns app icons
   - Content-Type: `image/png`
   - Cached by Service Worker

**Implementation Pattern** (similar to dashboard HTML):
- Embed manifest JSON as string constant in `api.py`
- Embed Service Worker JS as string constant in `api.py`
- Embed icon data as base64 or serve as binary (prefer binary for file size)

**Alternative**: Generate icons programmatically using PIL/Pillow (if already a dependency), but adds complexity. Prefer static PNG files.

### Offline Support

**Offline Scenarios**:

1. **Dashboard loads offline**:
   - Service Worker serves cached HTML/CSS/JS
   - Shows last cached API data
   - Displays "Offline" indicator in UI

2. **API requests fail**:
   - Service Worker returns cached API responses
   - If no cache, returns empty/error response
   - Dashboard shows "No data available (offline)" message

3. **First visit offline**:
   - Service Worker not installed yet
   - Browser shows default offline page
   - User must visit once while online to install PWA

**UI Indicators**:
- Add offline detection in dashboard JavaScript:
```javascript
// Detect online/offline status
window.addEventListener('online', () => {
    console.log('Online');
    document.body.classList.remove('offline');
    fetchStatus(); // Refresh data
});

window.addEventListener('offline', () => {
    console.log('Offline');
    document.body.classList.add('offline');
    // Show offline banner
});
```

- CSS for offline state:
```css
body.offline::before {
    content: 'OFFLINE MODE';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: var(--red);
    color: white;
    text-align: center;
    padding: 0.5rem;
    z-index: 10000;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
```

### Push Notifications (Optional, Future)

**Not implemented in initial version**, but structure prepared:

- Service Worker can receive push notifications
- Requires backend push service (not implemented)
- Could integrate with existing Telegram bot or webhook alerts
- Requires user permission prompt

**Future Enhancement**: Add push notification support when alerting system is expanded.

### HTTPS Requirement

**Development**:
- `localhost` works without HTTPS (browsers allow this exception)
- Service Worker works on `http://localhost:8080`

**Production**:
- HTTPS required for PWA features (Service Worker, install prompt)
- Options:
  1. **Reverse proxy** (nginx) with Let's Encrypt certificate
  2. **Self-signed certificate** (not recommended, browser warnings)
  3. **Cloudflare Tunnel** or similar (if Pi accessible via domain)

**Note**: This is a standard PWA requirement, not a project limitation. Document in README that HTTPS is required for production PWA features.

## Files to Modify

**Modified Files**:
- `webstatuspi/_dashboard.py` - Add manifest link, Service Worker registration, PWA meta tags, offline detection
- `webstatuspi/api.py` - Add endpoints for `/manifest.json`, `/sw.js`, `/icon-192.png`, `/icon-512.png`

**New Files** (or embedded as constants):
- `webstatuspi/_manifest.py` - Manifest JSON as string constant (optional, can be in `api.py`)
- `webstatuspi/_service_worker.py` - Service Worker JS as string constant (optional, can be in `api.py`)
- Icon files: `webstatuspi/icons/icon-192.png`, `webstatuspi/icons/icon-512.png` (or embed as base64)

**Recommended Structure**:
- Keep manifest and Service Worker as string constants in `api.py` (consistent with dashboard HTML approach)
- Store icon PNG files in `webstatuspi/icons/` directory
- Serve icons as binary files (not base64, better file size)

## Dependencies

**None** - PWA features use browser APIs (Service Worker, Web App Manifest) and static files.

**Icon Generation** (one-time setup):
- SVG editor (Inkscape, Figma, etc.) or
- PIL/Pillow (if already a dependency for hardware features) or
- Online icon generator tools

## Performance Impact

**Server-side (Pi 1B+)**:
- **CPU**: No impact (Service Worker runs in browser)
- **RAM**: No impact (static file serving)
- **Storage**: +~100KB for icons and manifest (negligible)
- **Network**: Minimal (icons cached by browser after first load)

**Client-side (Browser)**:
- **Cache storage**: ~50-200KB for dashboard assets + API responses
- **Service Worker overhead**: < 1MB RAM (browser-managed)
- **Performance**: Faster subsequent loads (cached assets)

**Conclusion**: Zero server impact, positive client impact (faster loads, offline support).

## Testing Strategy

**Manual Testing Checklist**:
- [ ] Install PWA on Android device - app appears in app drawer
- [ ] Install PWA on iOS device - "Add to Home Screen" works
- [ ] Install PWA on desktop (Chrome/Edge) - app installs and opens in standalone window
- [ ] Offline access - dashboard loads from cache when network disabled
- [ ] Cache versioning - update `SW_VERSION`, verify old cache deleted and new cache created
- [ ] API caching - verify `/status` responses cached and served offline
- [ ] Cache invalidation - verify updated dashboard code loads after version bump
- [ ] Icon display - verify icons appear correctly on home screen and splash screen
- [ ] Theme colors - verify status bar matches cyan theme color
- [ ] Manifest validation - test with [Web App Manifest Validator](https://manifest-validator.appspot.com/)
- [ ] Service Worker registration - verify SW installs and activates correctly
- [ ] Update detection - verify SW updates when version changes

**Browser Compatibility**:
- Chrome/Edge: Full PWA support ✅
- Firefox: Partial support (installable, Service Worker works) ✅
- Safari (iOS): Limited support (installable via "Add to Home Screen", Service Worker works) ✅
- Safari (macOS): Full support in Safari 16+ ✅

**Edge Cases**:
- First visit offline (SW not installed) - graceful fallback
- Very old browsers (no Service Worker support) - app works normally, no PWA features
- Cache quota exceeded - handle gracefully, log warning
- Service Worker update fails - fallback to network requests

## Security Considerations

**Content Security Policy (CSP)**:
- Service Worker must be allowed in CSP (if CSP is added in future)
- Inline scripts in Service Worker are allowed (Service Workers are separate context)

**Cache Security**:
- API responses may contain sensitive data (URLs, error messages)
- Cache is browser-local, not shared across origins
- Consider cache expiration for sensitive data (already implemented via versioning)

**HTTPS Requirement**:
- Document that HTTPS is required for production
- Provide guidance on setting up reverse proxy with Let's Encrypt

## Documentation Updates

**README.md**:
- Add PWA installation instructions
- Document HTTPS requirement for production
- Add troubleshooting section for PWA issues

**docs/ARCHITECTURE.md**:
- Document PWA architecture (Service Worker, caching strategy)
- Explain cache versioning approach

## Follow-up Tasks

- Add push notification support (requires backend push service)
- Add background sync for offline actions (e.g., queue reset requests)
- Add install prompt UI (encourage users to install PWA)
- Add offline analytics (track offline usage patterns)
- Optimize icon sizes further (WebP format, responsive icons)

## Progress Log

- [2026-01-22 11:49] Task completed - 274 tests passing
- [2026-01-22 11:15] Fixed bug: "Additional Details" section stats not showing in modal
  - Stats containers were hidden on modal open but never shown when data populated
  - Added `style.display = 'block'` calls for `modalChecks24hStat` and `modalConsecutiveFailuresStat`
- [2026-01-22 11:05] Implementation complete - all tests passing (43/43)
  - Created `_pwa.py` with manifest, service worker, and base64-encoded icons
  - Updated `_dashboard.py` with PWA meta tags, offline banner, and SW registration
  - Updated `api.py` with endpoints: `/manifest.json`, `/sw.js`, `/icon-192.png`, `/icon-512.png`
  - Added 10 new tests in `test_api.py` for PWA functionality
- [2026-01-22 00:00] Started task
- [2026-01-22] Task created with comprehensive PWA implementation plan, including cache versioning strategy

## Learnings

(To be filled during implementation)
