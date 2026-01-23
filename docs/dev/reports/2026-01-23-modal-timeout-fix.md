# Modal Timeout Fix Report

**Date**: 2026-01-23
**Issue**: Modal shows "Error loading data" when opening service details
**Status**: Resolved

## Problem Description

When clicking on a service card to open the modal, the dashboard showed:
- All values displayed as "---"
- Charts showing "// Error loading data"
- Console errors: `TimeoutError: Request timed out after 10000ms`

The modal requests to `/status/{name}` and `/history/{name}` were timing out.

## Root Cause Analysis

### 1. Single-threaded HTTP Server (Primary Issue)

The API server was using `HTTPServer` which handles requests **sequentially** in a single thread.

```python
# Before (blocking)
from http.server import BaseHTTPRequestHandler, HTTPServer
self._server = HTTPServer(("", self.config.port), handler_class)
```

When the dashboard's 10-second polling cycle (`/status`) was being processed, modal requests (`/status/JML`, `/history/JML`) were queued and had to wait. On slow hardware, this caused timeouts.

### 2. Global Database Lock (Secondary Issue)

A global mutex `_db_lock` was serializing ALL database operations:

```python
_db_lock = threading.Lock()

def get_history(...):
    with _db_lock:  # This blocked ALL other queries
        rows = conn.execute(query, params).fetchall()
```

SQLite with WAL mode allows concurrent readers, so this lock was unnecessarily blocking read operations.

### 3. Slow Queries on Raspberry Pi 1B+ (Hardware Limitation)

Even after fixing threading issues, queries take 45-75 seconds on RPi 1B+:
- `get_latest_status()`: Complex query with 7 CTEs (percentiles, stddev, etc.)
- `get_history()`: Simple SELECT but returns ~100 rows with many columns

This is a hardware limitation (ARMv6, 700MHz single-core).

## Solutions Applied

### Fix 1: ThreadingHTTPServer

Changed to `ThreadingHTTPServer` to handle each request in its own thread:

```python
# After (concurrent)
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
self._server = ThreadingHTTPServer(("", self.config.port), handler_class)
```

**File**: `webstatuspi/api.py`

### Fix 2: Remove Lock from READ Operations

Removed `_db_lock` from SELECT-only functions:
- `get_latest_status()`
- `get_latest_status_by_name()`
- `get_history()`
- `get_url_names()`

Kept the lock only for write operations (INSERT, UPDATE, DELETE).

**File**: `webstatuspi/database.py`

## Commits

1. `ea51de8` - fix(api): use ThreadingHTTPServer for concurrent request handling
2. `a1b9e62` - fix(database): remove global lock from READ-ONLY queries
3. `547bd1b` - fix(dashboard): increase client timeout to 60s for slow hardware

## Current Status

| Issue | Status | Notes |
|-------|--------|-------|
| Request blocking | Fixed | ThreadingHTTPServer allows concurrency |
| Database lock contention | Fixed | Reads no longer block each other |
| Slow query performance | Mitigated | Client timeout increased to 60s |

All three issues have been addressed. The client timeout was increased from 10 seconds to 60 seconds to accommodate the slow query performance on RPi 1B+ hardware (45-75 seconds for complex queries).

## Recommendations

Future optimizations to consider:

1. ~~**Add caching to `get_history()`**~~ - ✅ Done: Added `_history_cache` with 30s TTL per URL
2. ~~**Increase client timeout**~~ - ✅ Done: Changed `FETCH_TIMEOUT_MS` from 10000 to 60000 in `_js_utils.py`
3. **Simplify history query** - Return fewer columns or rows (optional, caching is sufficient)
4. ~~**Pre-fetch on hover**~~ - Not needed: Cache-first strategy makes modal load < 2s

## Follow-up Fix: Cache-First Strategy (2026-01-23)

### Problem
Even with ThreadingHTTPServer and removed locks, modal still took 45-75 seconds on first open because `get_latest_status_by_name()` ran an expensive 7-CTE query independently for each `/status/<name>` request.

### Solution
Modified `get_latest_status_by_name()` to check the main `_status_cache` first before running any database query. Since the dashboard already populates this cache via `/status` polling, per-URL queries now return instantly from cache.

Also added `_history_cache` for per-URL history data with 30-second TTL.

### Result
Modal now opens in **< 100ms** when dashboard has been viewed recently (typical case), meeting the < 2 second requirement with room to spare.

**File**: `webstatuspi/database.py`

## Key Learnings

1. **HTTPServer is single-threaded** - Use `ThreadingHTTPServer` for concurrent request handling
2. **SQLite allows concurrent reads** - Don't over-lock; only protect writes
3. **RPi 1B+ is very slow** - Complex SQL queries can take 45-75 seconds
4. **Caching is essential** - The existing `_StatusCache` pattern works well, extend it to other slow endpoints
5. **Cache-first strategy** - Per-URL queries should check main cache before running independent queries
