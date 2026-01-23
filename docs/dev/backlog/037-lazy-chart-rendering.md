# Task #037: Lazy Chart Rendering

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: Dashboard, WPO
- **Created**: 2026-01-23
- **Started**: -
- **Completed**: -
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a dashboard user, I want charts to render only when I view the Analytics tab so that the modal opens faster.

**Acceptance Criteria**:
- [ ] Charts render only when Analytics tab is active
- [ ] Charts render incrementally using `requestAnimationFrame`
- [ ] Track rendered charts to avoid re-rendering
- [ ] Clear rendered state when modal closes
- [ ] Trigger chart rendering when switching to Analytics tab

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

(empty)

## Learnings

(empty)
