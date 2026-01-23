# Task #036: Debounce Polling During Inactive Tabs

## Metadata
- **Status**: completed
- **Priority**: P2
- **Slice**: Dashboard, WPO
- **Created**: 2026-01-23
- **Started**: 2026-01-23
- **Completed**: 2026-01-23
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a mobile user, I want the dashboard to reduce polling when the tab is inactive so that battery and network resources are conserved.

**Acceptance Criteria**:
- [x] Detect tab visibility changes via `visibilitychange` event
- [x] Slow polling to 5x interval when tab is inactive
- [x] Resume normal polling immediately when tab becomes active
- [x] Fetch fresh data immediately when tab becomes active

## Implementation Notes

### Modify polling logic in `_js_core.py`

```javascript
let pollInterval = null;
let isTabActive = true;

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);

    const interval = isTabActive ? POLL_INTERVAL : POLL_INTERVAL * 5;

    pollInterval = setInterval(() => {
        if (isTabActive) {
            fetchStatus();
        }
    }, interval);
}

document.addEventListener('visibilitychange', () => {
    isTabActive = !document.hidden;

    if (isTabActive) {
        fetchStatus();
        startPolling();
    } else {
        startPolling();
    }
});

startPolling();
```

### Remove existing `setInterval` call

Current code likely has a simple `setInterval(fetchStatus, POLL_INTERVAL)` that needs to be replaced with the `startPolling()` approach.

## Expected Impact

- **Network requests**: 80% reduction when tab inactive
- **Battery usage**: 20-30% reduction on mobile devices

## Files to Modify

- `webstatuspi/_dashboard/_js_core.py` - Replace polling logic

## Dependencies

None

## Progress Log

### 2026-01-23 - Implementation Complete

- ✅ Added `isTabActive` and `pollInterval` variables to track visibility state
- ✅ Implemented `startPolling()` function that adjusts interval based on tab visibility
- ✅ Added `visibilitychange` event listener to detect tab state changes
- ✅ When tab becomes active: fetches immediately and restarts fast polling
- ✅ When tab becomes inactive: slows polling to 5x interval (50s instead of 10s)

**Implementation approach:**
- Uses `document.hidden` to check visibility state
- Restarts polling with new interval when state changes
- Only fetches when tab is active (skips fetch during inactive polling)

## Learnings

(empty)
