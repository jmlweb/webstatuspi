# Task #036: Debounce Polling During Inactive Tabs

## Metadata
- **Status**: pending
- **Priority**: P2
- **Slice**: Dashboard, WPO
- **Created**: 2026-01-23
- **Started**: -
- **Completed**: -
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a mobile user, I want the dashboard to reduce polling when the tab is inactive so that battery and network resources are conserved.

**Acceptance Criteria**:
- [ ] Detect tab visibility changes via `visibilitychange` event
- [ ] Slow polling to 5x interval when tab is inactive
- [ ] Resume normal polling immediately when tab becomes active
- [ ] Fetch fresh data immediately when tab becomes active

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

(empty)

## Learnings

(empty)
