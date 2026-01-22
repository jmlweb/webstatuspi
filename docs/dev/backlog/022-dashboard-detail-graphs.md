# Task #022: Dashboard Detail Modal - Graph Visualization Panel

## Metadata
- **Status**: in_progress
- **Priority**: P1 - Active
- **Slice**: Frontend, Dashboard, API
- **Created**: 2026-01-22
- **Started**: 2026-01-21
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a system administrator, I want to see visual graphs and charts in the detail modal instead of just a table list, so that I can quickly identify patterns, trends, and anomalies in the monitoring data (response times, uptime patterns, status code distribution).

**Acceptance Criteria**:
- [ ] Replace or complement the history table with visual graph panels
- [ ] Response time over time line chart (24h window)
- [ ] Uptime/downtime timeline visualization (area chart showing up/down periods)
- [ ] Status code distribution chart (bar or pie chart)
- [ ] Response time distribution histogram (shows latency patterns)
- [ ] All graphs use vanilla JavaScript (no external charting libraries)
- [ ] Graphs maintain cyberpunk/CRT aesthetic consistent with dashboard
- [ ] Graphs are responsive and work on mobile devices
- [ ] Performance: Graphs render in < 500ms on Pi 1B+ (client-side rendering)
- [ ] Graphs update when modal is reopened (fresh data fetch)

## Implementation Notes

### Current State Analysis

The detail modal (`#historyModal`) currently shows:
1. **Summary section** (`.modal-summary`): 4 stat cards (Status, Code, Latency, Uptime 24h)
2. **History table** (`.history-table`): Tabular list of checks with columns: Time, Status, Code, Latency, Error

**Data available**:
- `/status/<name>`: Current status with all UrlStatus fields
- `/history/<name>`: Array of check results (last 24h, max 100 records) with:
  - `checked_at`: ISO timestamp
  - `is_up`: boolean
  - `status_code`: int | null
  - `response_time_ms`: int | null
  - `error`: string | null

### Graph Design Requirements

#### 1. Response Time Over Time (Line Chart)
- **X-axis**: Time (last 24 hours, formatted as HH:MM)
- **Y-axis**: Response time in milliseconds (0-2000ms scale, auto-scale if needed)
- **Data**: Plot `response_time_ms` vs `checked_at` for all checks
- **Visual**: Cyan line with glow effect, points at each check
- **Interactivity**: Hover shows exact timestamp and response time
- **Empty states**: Show "No data" message if no checks available

#### 2. Uptime/Downtime Timeline (Area Chart)
- **X-axis**: Time (last 24 hours)
- **Y-axis**: Binary status (UP=1, DOWN=0) or stacked area
- **Data**: Plot `is_up` status over time
- **Visual**: 
  - Green area for UP periods (`var(--green)`)
  - Red area for DOWN periods (`var(--red)`)
  - Smooth transitions between states
- **Purpose**: Quickly identify downtime periods and duration

#### 3. Status Code Distribution (Bar Chart)
- **X-axis**: HTTP status codes (200, 301, 404, 500, etc.)
- **Y-axis**: Count of occurrences
- **Data**: Group checks by `status_code`, count occurrences
- **Visual**: 
  - Vertical bars with height proportional to count
  - Color coding: 2xx=green, 3xx=cyan, 4xx=yellow, 5xx=red
  - Show count label on top of each bar
- **Empty states**: Show "No status codes" if all null

#### 4. Response Time Distribution (Histogram)
- **X-axis**: Response time buckets (0-100ms, 100-200ms, 200-500ms, 500-1000ms, 1000-2000ms, >2000ms)
- **Y-axis**: Count of checks in each bucket
- **Data**: Group `response_time_ms` values into buckets
- **Visual**: 
  - Horizontal or vertical bars
  - Color gradient: green (fast) → yellow → orange → red (slow)
  - Show percentage labels
- **Purpose**: Understand latency distribution patterns

### Technical Implementation

#### Vanilla JavaScript Charting Approach

**No external libraries** (Chart.js, D3.js, etc.) to maintain zero dependencies and Pi 1B+ performance.

**Use SVG for rendering**:
- SVG is lightweight, scalable, and works well with CSS
- Can be styled with CSS custom properties (cyberpunk colors)
- Supports animations via CSS transitions
- No canvas context overhead

**Chart rendering pattern**:
```javascript
function renderLineChart(container, data, options) {
    // 1. Calculate dimensions and scales
    const width = container.clientWidth;
    const height = 200; // Fixed or responsive
    const padding = { top: 20, right: 20, bottom: 30, left: 50 };
    
    // 2. Create SVG element
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', width);
    svg.setAttribute('height', height);
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    
    // 3. Calculate scales (time → x, value → y)
    const xScale = calculateXScale(data, width, padding);
    const yScale = calculateYScale(data, width, padding);
    
    // 4. Draw axes (lines, labels)
    drawAxes(svg, xScale, yScale, padding);
    
    // 5. Draw data (line path, points)
    drawLine(svg, data, xScale, yScale);
    
    // 6. Add interactivity (hover tooltips)
    addTooltips(svg, data, xScale, yScale);
    
    // 7. Append to container
    container.appendChild(svg);
}
```

#### Graph Container Layout

Replace or complement `.modal-body` section:

```html
<section class="modal-body" aria-label="Service analytics">
    <!-- Graph grid layout -->
    <div class="graphs-grid">
        <!-- Row 1: Time series charts (full width) -->
        <div class="graph-panel graph-panel-wide">
            <h3 class="graph-title">Response Time Over Time</h3>
            <div class="graph-container" id="responseTimeChart"></div>
        </div>
        
        <!-- Row 2: Uptime timeline (full width) -->
        <div class="graph-panel graph-panel-wide">
            <h3 class="graph-title">Uptime Timeline</h3>
            <div class="graph-container" id="uptimeChart"></div>
        </div>
        
        <!-- Row 3: Distribution charts (side by side) -->
        <div class="graph-panel">
            <h3 class="graph-title">Status Code Distribution</h3>
            <div class="graph-container" id="statusCodeChart"></div>
        </div>
        
        <div class="graph-panel">
            <h3 class="graph-title">Response Time Distribution</h3>
            <div class="graph-container" id="latencyHistogram"></div>
        </div>
    </div>
    
    <!-- Optional: Keep table as collapsible section or remove -->
    <details class="history-table-section">
        <summary>Raw History Data</summary>
        <table class="history-table">...</table>
    </details>
</section>
```

#### CSS Styling for Graphs

```css
.graphs-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.5rem;
    padding: 1.5rem;
}

.graph-panel {
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid var(--border);
    padding: 1rem;
    clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px));
}

.graph-panel-wide {
    grid-column: 1 / -1;
}

.graph-title {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--cyan);
    margin-bottom: 0.75rem;
    text-shadow: 0 0 8px var(--cyan);
}

.graph-container {
    width: 100%;
    height: 200px; /* Adjust per chart type */
    position: relative;
}

.graph-container svg {
    width: 100%;
    height: 100%;
}

/* Chart line styles */
.chart-line {
    stroke: var(--cyan);
    stroke-width: 2;
    fill: none;
    filter: drop-shadow(0 0 4px var(--cyan));
}

.chart-point {
    fill: var(--cyan);
    stroke: var(--bg-dark);
    stroke-width: 1;
    r: 3;
    transition: r 0.2s ease;
}

.chart-point:hover {
    r: 5;
    filter: drop-shadow(0 0 8px var(--cyan));
}

/* Axis styles */
.chart-axis {
    stroke: var(--text-dim);
    stroke-width: 1;
}

.chart-axis-label {
    font-size: 0.65rem;
    fill: var(--text-dim);
    text-anchor: middle;
}

/* Tooltip */
.chart-tooltip {
    position: absolute;
    background: var(--bg-panel);
    border: 1px solid var(--cyan);
    padding: 0.5rem;
    font-size: 0.7rem;
    color: var(--text);
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.2s ease;
    z-index: 100;
    box-shadow: 0 0 10px rgba(0, 255, 249, 0.3);
}

.chart-tooltip.visible {
    opacity: 1;
}
```

#### JavaScript Functions to Implement

**Core charting functions** (in `_dashboard.py` script section):

1. `renderResponseTimeChart(container, historyData)` - Line chart
2. `renderUptimeTimeline(container, historyData)` - Area chart
3. `renderStatusCodeChart(container, historyData)` - Bar chart
4. `renderLatencyHistogram(container, historyData)` - Histogram
5. `calculateTimeScale(data, width, padding)` - X-axis scale helper
6. `calculateValueScale(data, min, max, height, padding)` - Y-axis scale helper
7. `formatTimeLabel(timestamp)` - Format timestamp for axis labels
8. `createTooltip(element)` - Create and position tooltip

**Data processing functions**:

1. `groupByStatusCode(checks)` - Group checks by status code, return `{200: 45, 500: 2, ...}`
2. `bucketResponseTimes(checks)` - Group response times into buckets
3. `filterValidData(checks, field)` - Filter out null/undefined values

**Integration with existing modal**:

- Update `fetchHistory(urlName)` to call graph rendering functions after data is loaded
- Update `renderHistoryTable(checks)` to also render graphs (or replace table)
- Clear graphs when modal is closed (`closeModal()`)

### Performance Considerations

**Pi 1B+ Constraints**:
- **CPU**: Single-core 700MHz ARM11 - minimize calculations
- **RAM**: ~256MB available - avoid large data structures
- **Rendering**: Client-side SVG is efficient, but limit data points

**Optimizations**:
1. **Data sampling**: If > 100 data points, sample to ~50-60 points for line charts (every Nth point)
2. **Lazy rendering**: Only render visible graphs (use IntersectionObserver if needed)
3. **Debounce tooltips**: Don't update tooltip on every mouse move, use 50ms debounce
4. **Cache scales**: Reuse scale calculations if data hasn't changed
5. **SVG reuse**: Don't recreate SVG elements, update existing ones

**Performance targets**:
- Graph rendering: < 500ms total for all 4 graphs
- Memory: < 5MB additional for graph data structures
- CPU: < 10% spike during rendering (acceptable for modal open)

### Accessibility

- **ARIA labels**: Each graph container needs `aria-label` describing the chart
- **Keyboard navigation**: Not required for graphs (visual only), but ensure modal remains keyboard accessible
- **Screen readers**: Provide text summary of graph data (e.g., "Response time averaged 234ms over 24 hours")
- **Color contrast**: Ensure graph colors meet WCAG AA standards
- **Focus management**: Graphs don't need focus, but tooltips should be keyboard accessible if shown

### Responsive Design

**Mobile considerations**:
- Stack graphs vertically on small screens
- Reduce graph height on mobile (150px instead of 200px)
- Simplify axis labels (show fewer ticks)
- Touch-friendly tooltips (show on tap, not hover)

**Breakpoints**:
- Desktop: 4 graphs in grid (2 wide, 2 side-by-side)
- Tablet: Stack all graphs vertically
- Mobile: Stack all graphs, reduce padding

### Testing Strategy

**Manual testing checklist**:
- [ ] Open modal with URL that has 100+ checks - graphs render correctly
- [ ] Open modal with URL that has < 10 checks - graphs show "No data" gracefully
- [ ] Open modal with URL that has all null response times - graphs handle gracefully
- [ ] Hover over line chart points - tooltip shows correct data
- [ ] Resize browser window - graphs resize responsively
- [ ] Open modal on mobile device - graphs stack vertically
- [ ] Close and reopen modal - graphs refresh with new data
- [ ] Performance: Open modal on Pi 1B+ - rendering completes in < 500ms

**Edge cases to handle**:
- Empty history data (no checks)
- All null response times
- All null status codes
- Single data point (can't draw line)
- Very large response times (> 2000ms) - auto-scale Y-axis
- Time gaps in data (missing checks) - show gaps in line chart

## Files to Modify

**Modified Files**:
- `webstatuspi/_dashboard.py` - Add graph rendering JavaScript functions, update modal HTML structure, add graph CSS styles

**No backend changes required** - existing `/history/<name>` endpoint provides all needed data.

## Dependencies

**None** - uses vanilla JavaScript, SVG, and existing API endpoints.

## Follow-up Tasks

- Consider adding time range selector (1h, 6h, 24h, 7d) for graphs
- Consider adding export functionality (download graph as PNG/SVG)
- Consider adding real-time graph updates (WebSocket or polling)

## Progress Log

- [2026-01-22 08:30] Implementation complete:
  - Added ~200 lines of CSS for graph styling (grid layout, panels, SVG charts, tooltips)
  - Implemented 4 chart types using vanilla JavaScript and SVG:
    - Response time line chart with hover tooltips
    - Uptime timeline with colored status blocks
    - Status code distribution bar chart (color-coded by status class)
    - Latency distribution histogram (color gradient by speed)
  - Updated modal HTML with graphs grid and collapsible history table
  - Integrated charts with fetchHistory() lifecycle
  - All code verified syntactically correct (balanced braces/parens/brackets)
- [2026-01-21 10:00] Started task implementation
- [2026-01-22] Task created with comprehensive implementation plan

## Learnings

(To be filled during implementation)
