# Task #035: Request Deduplication

## Metadata
- **Status**: completed
- **Priority**: P2
- **Slice**: Dashboard, WPO
- **Created**: 2026-01-23
- **Started**: 2026-01-23
- **Completed**: 2026-01-23
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a dashboard user, I want rapid clicks on the same card to share a single network request so that resources are not wasted on duplicate requests.

**Acceptance Criteria**:
- [x] Track in-flight requests per URL name
- [x] Return existing promise if request already in flight
- [x] Clean up tracking on request completion (success or failure)
- [x] All concurrent callers receive the same response

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

### 2026-01-23 - Implementation Complete

- ✅ Added `inFlightRequests` Map to track pending requests per URL name
- ✅ Modified `fetchHistory()` to check for existing promises before creating new requests
- ✅ Implemented cleanup in finally block to remove tracking when request completes
- ✅ All concurrent clicks on same card now share single network request

**Implementation approach:**
- Used Map instead of object for better key handling
- Wrapped fetch logic in async IIFE to ensure cleanup via finally
- Returns existing promise immediately if request already in flight

## Learnings

(empty)
