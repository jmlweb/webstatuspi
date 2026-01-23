# Task #035: Request Deduplication

## Metadata
- **Status**: pending
- **Priority**: P2
- **Slice**: Dashboard, WPO
- **Created**: 2026-01-23
- **Started**: -
- **Completed**: -
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a dashboard user, I want rapid clicks on the same card to share a single network request so that resources are not wasted on duplicate requests.

**Acceptance Criteria**:
- [ ] Track in-flight requests per URL name
- [ ] Return existing promise if request already in flight
- [ ] Clean up tracking on request completion (success or failure)
- [ ] All concurrent callers receive the same response

## Implementation Notes

### Add to `_js_core.py`

```javascript
const inFlightRequests = new Map();

async function fetchHistory(urlName) {
    if (inFlightRequests.has(urlName)) {
        return inFlightRequests.get(urlName);
    }

    const requestPromise = (async () => {
        try {
            const [statusRes, historyRes] = await Promise.all([
                fetchWithTimeout('/status/' + encodeURIComponent(urlName)),
                fetchWithTimeout('/history/' + encodeURIComponent(urlName))
            ]);

            if (!statusRes.ok || !historyRes.ok) {
                throw new Error('Failed to fetch data');
            }

            const [statusData, historyData] = await Promise.all([
                statusRes.json(),
                historyRes.json()
            ]);

            return { status: statusData, history: historyData };
        } finally {
            inFlightRequests.delete(urlName);
        }
    })();

    inFlightRequests.set(urlName, requestPromise);
    return requestPromise;
}
```

## Expected Impact

- **Network requests**: 30-50% reduction in duplicate requests
- **Server load**: Lower CPU usage on Raspberry Pi

## Files to Modify

- `webstatuspi/_dashboard/_js_core.py` - Replace current `fetchHistory()` implementation

## Dependencies

None

## Progress Log

(empty)

## Learnings

(empty)
