# Task #037: Lazy Chart Rendering

## Metadata
- **Status**: completed
- **Priority**: P3
- **Slice**: Dashboard, WPO
- **Created**: 2026-01-23
- **Started**: 2026-01-24
- **Completed**: 2026-01-24
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a dashboard user, I want charts to render only when I view the Analytics tab so that the modal opens faster.

**Acceptance Criteria**:
- [x] Charts render only when Analytics tab is active
- [x] Charts render incrementally using `requestAnimationFrame`
- [x] Track rendered charts to avoid re-rendering
- [x] Clear rendered state when modal closes
- [x] Trigger chart rendering when switching to Analytics tab

## Implementation Notes

### Modify chart rendering in `_js_core.py`

```javascript
const renderedCharts = new Set();

function renderAllCharts(checks) {
    const graphsTab = document.getElementById('graphsTab');

    if (!graphsTab.classList.contains('active')) {
        return;
    }

    const charts = [
        { id: 'responseTimeChart', fn: renderResponseTimeChart },
        { id: 'uptimeChart', fn: renderUptimeChart },
        { id: 'statusCodeChart', fn: renderStatusCodeChart },
        { id: 'latencyHistogram', fn: renderLatencyHistogram }
    ];

    let chartIndex = 0;
    function renderNext() {
        if (chartIndex >= charts.length) return;

        requestAnimationFrame(() => {
            const chart = charts[chartIndex];
            const container = document.getElementById(chart.id);
            if (container && !renderedCharts.has(chart.id)) {
                chart.fn(container, checks);
                renderedCharts.add(chart.id);
            }
            chartIndex++;
            renderNext();
        });
    }

    renderNext();
}

function switchTab(tabName) {
    // ... existing tab switching code ...

    if (tabName === 'graphs' && currentUrlData) {
        if (renderedCharts.size === 0) {
            renderAllCharts(currentUrlData.checks);
        }
    }
}

function closeModal() {
    // ... existing close logic ...
    renderedCharts.clear();
}
```

## Expected Impact

- **TTI for modal**: 200ms → 50ms (75% improvement)
- **FCP for modal**: Immediate content vs. waiting for charts

## Files to Modify

- `webstatuspi/_dashboard/_js_core.py` - Modify `renderAllCharts()`, `switchTab()`, `closeModal()`

## Dependencies

None

## Progress Log

**2026-01-24**:
- Implemented `renderAllChartsLazy()` function with `requestAnimationFrame` for incremental rendering
- Added `renderedCharts` Set to track which charts have been rendered
- Modified `fetchHistory()` to conditionally render charts only when Analytics tab is active
- Updated `switchTab()` to trigger lazy rendering when switching to Analytics tab
- Modified `closeModal()` to clear rendered charts state for fresh rendering on next open
- All 399 tests pass

## Learnings

**L024: requestAnimationFrame enables non-blocking incremental rendering**
- Using `requestAnimationFrame` in a recursive pattern allows rendering multiple charts incrementally without blocking the main thread
- Charts render one per frame, making modal content visible immediately while charts load progressively
- This pattern is especially important on resource-constrained devices like RPi 1B+ where chart rendering can be CPU-intensive
