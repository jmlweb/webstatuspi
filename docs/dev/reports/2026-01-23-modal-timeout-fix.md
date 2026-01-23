# Modal Timeout Fix Report

**Date**: 2026-01-23
**Issue**: Modal shows "Error loading data" when opening service details
**Status**: Partially resolved

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

## Current Status

| Issue | Status | Notes |
|-------|--------|-------|
| Request blocking | Fixed | ThreadingHTTPServer allows concurrency |
| Database lock contention | Fixed | Reads no longer block each other |
| Slow query performance | Not fixed | Hardware limitation on RPi 1B+ |

The modal still times out because queries take 45+ seconds on RPi 1B+, exceeding the 10-second client timeout. However, the **concurrency issues** are resolved - requests no longer block each other.

## Recommendations

To fully resolve the timeout issue, consider:

1. **Add caching to `get_history()`** - Similar to existing `_StatusCache` for `get_latest_status()`
2. **Increase client timeout** - Change `FETCH_TIMEOUT_MS` from 10000 to 60000 in `_js_utils.py`
3. **Simplify history query** - Return fewer columns or rows
4. **Pre-fetch on hover** - Start loading data when user hovers over a card (see backlog task #034)

## Key Learnings

1. **HTTPServer is single-threaded** - Use `ThreadingHTTPServer` for concurrent request handling
2. **SQLite allows concurrent reads** - Don't over-lock; only protect writes
3. **RPi 1B+ is very slow** - Complex SQL queries can take 45-75 seconds
4. **Caching is essential** - The existing `_StatusCache` pattern works well, extend it to other slow endpoints
