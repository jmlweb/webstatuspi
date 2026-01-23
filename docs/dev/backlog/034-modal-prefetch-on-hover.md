# Task #034: Modal Data Prefetching on Hover

## Metadata
- **Status**: pending
- **Priority**: P2
- **Slice**: Dashboard, WPO
- **Created**: 2026-01-23
- **Started**: -
- **Completed**: -
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a dashboard user, I want modal data to be prefetched when I hover over a card so that the modal opens instantly without loading delay.

**Acceptance Criteria**:
- [ ] Prefetch `/status/<name>` and `/history/<name>` on card hover
- [ ] Cache prefetched data with 5-second TTL
- [ ] Use cached data when opening modal if available
- [ ] Debounce prefetch with 150ms delay to avoid excessive requests
- [ ] Support touch devices via `touchstart` event
- [ ] Fallback to normal fetch if cache miss or expired

## Implementation Notes

### Add to `_js_core.py`

```javascript
let prefetchCache = new Map();
let prefetchTimeout = null;

function prefetchModalData(urlName) {
    if (prefetchCache.has(urlName)) return;

    clearTimeout(prefetchTimeout);
    prefetchTimeout = setTimeout(() => {
        Promise.all([
            fetchWithTimeout('/status/' + encodeURIComponent(urlName)),
            fetchWithTimeout('/history/' + encodeURIComponent(urlName))
        ]).then(([statusRes, historyRes]) => {
            if (statusRes.ok && historyRes.ok) {
                Promise.all([statusRes.json(), historyRes.json()])
                    .then(([statusData, historyData]) => {
                        prefetchCache.set(urlName, {
                            status: statusData,
                            history: historyData,
                            timestamp: Date.now()
                        });
                    });
            }
        }).catch(() => {});
    }, 150);
}

// Mouse hover (desktop)
document.getElementById('cardsContainer').addEventListener('mouseenter', function(e) {
    const card = e.target.closest('.card');
    if (card?.dataset.urlName) prefetchModalData(card.dataset.urlName);
}, true);

// Touch start (mobile)
document.getElementById('cardsContainer').addEventListener('touchstart', function(e) {
    const card = e.target.closest('.card');
    if (card?.dataset.urlName) prefetchModalData(card.dataset.urlName);
}, { passive: true });
```

### Modify `openModal()` function

```javascript
function openModal(urlName) {
    // ... existing modal setup code ...

    const cached = prefetchCache.get(urlName);
    if (cached && (Date.now() - cached.timestamp < 5000)) {
        updateModalSummary(cached.status);
        renderHistoryTable(cached.history.checks);
        renderAllCharts(cached.history.checks);
        prefetchCache.delete(urlName);
    } else {
        fetchHistory(urlName);
    }
}
```

## Expected Impact

- **TTI for modal**: ~300ms → ~50ms (83% improvement)
- **FCP for modal**: Immediate vs. 200-500ms delay

## Files to Modify

- `webstatuspi/_dashboard/_js_core.py` - Add prefetch logic and modify `openModal()`

## Dependencies

None

## Progress Log

(empty)

## Learnings

(empty)
