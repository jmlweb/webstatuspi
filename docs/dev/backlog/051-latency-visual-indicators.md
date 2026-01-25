# Task #051: Enhanced Latency Visual Indicators

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: Dashboard, Frontend
- **Created**: 2026-01-25
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a dashboard user, I want clearer visual indicators for latency states so I can immediately identify performance issues without reading numbers.

**Acceptance Criteria**:
- [ ] Add color-coded latency thresholds with visual feedback
- [ ] Enhance existing `[!]` warning indicators with better styling
- [ ] Add subtle background color changes to latency metric boxes based on state
- [ ] Ensure color changes meet WCAG AA contrast requirements
- [ ] Maintain existing latency class system (success/warning/danger)
- [ ] Add smooth transitions for state changes

## Implementation Notes

### Enhanced Latency Classes

Current classes: `success`, `warning`, `danger` (empty string for normal)

```css
/* In _css.py - Enhance .metric for latency */
.metric:nth-child(2) {  /* Latency metric (second in grid) */
    transition: var(--transition-fast);
}

/* Latency state indicators via data attribute */
.metric[data-latency-state="success"] {
    background: rgba(var(--green-rgb), 0.1);
    border-color: rgba(var(--green-rgb), 0.3);
}

.metric[data-latency-state="warning"] {
    background: rgba(var(--yellow-rgb), 0.1);
    border-color: rgba(var(--yellow-rgb), 0.3);
}

.metric[data-latency-state="danger"] {
    background: rgba(var(--red-rgb), 0.1);
    border-color: rgba(var(--red-rgb), 0.3);
    animation: subtle-pulse 2s infinite;
}

@keyframes subtle-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.9; }
}
```

### JavaScript Changes in `_js_core.py`

```javascript
function renderCard(url) {
    // ... existing code ...
    
    const latencyState = getLatencyState(url.response_time_ms);
    
    return `
        <article class="card${cardClass}" ...>
            <!-- ... existing header ... -->
            <div class="card-metrics" aria-hidden="true">
                <!-- ... Status metric ... -->
                <div class="metric" data-latency-state="${latencyState}">
                    <div class="metric-label">Latency</div>
                    <div class="metric-value">${formatResponseTimeWithWarning(url.response_time_ms)}</div>
                    <!-- ... progress bar ... -->
                </div>
                <!-- ... rest of metrics ... -->
            </div>
        </article>
    `;
}

function getLatencyState(ms) {
    if (ms === null || ms === undefined || ms === 0) return '';
    if (ms < 200) return 'success';
    if (ms < 500) return '';
    if (ms < 1000) return 'warning';
    return 'danger';
}
```

### Enhanced Warning Prefix Styling

```css
.latency-warning-prefix {
    font-size: 0.7rem;
    font-weight: 700;
    margin-right: 0.25rem;
    display: inline-block;
    animation: blink-warning 1.5s infinite;
}

.latency-warning-prefix.warning {
    color: var(--yellow);
    text-shadow: var(--glow-yellow);
}

.latency-warning-prefix.danger {
    color: var(--red);
    text-shadow: 0 0 8px var(--red);
    animation: blink-danger 1s infinite;
}

@keyframes blink-warning {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

@keyframes blink-danger {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}
```

## Expected Impact

- **Visual clarity**: Immediate identification of latency issues via color coding
- **Accessibility**: Better contrast and visual feedback
- **User experience**: Faster problem identification
- **Performance**: Minimal impact (CSS transitions, no layout shifts)

## Files to Modify

- `webstatuspi/_dashboard/_css.py` - Add latency state styles and animations
- `webstatuspi/_dashboard/_js_core.py` - Add `getLatencyState()` and data attribute

## Dependencies

None

## Progress Log

- **2026-01-25**: Task created based on dashboard design review

## Learnings

- Color-coded states improve at-a-glance comprehension
- Subtle animations draw attention without being distracting
- Background colors provide context without overwhelming the cyberpunk aesthetic