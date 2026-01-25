# Task #053: Enhanced Informative Tooltips

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: Dashboard, Frontend
- **Created**: 2026-01-25
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a dashboard user, I want informative tooltips on hover to understand what each metric means and how to interpret the values without leaving the dashboard.

**Acceptance Criteria**:
- [ ] Add tooltips to all metric labels (Status, Latency, Uptime)
- [ ] Add tooltips to progress bars explaining their scale
- [ ] Add tooltips to warning indicators (`[!]`) explaining thresholds
- [ ] Ensure tooltips are accessible (keyboard navigation, screen readers)
- [ ] Style tooltips to match cyberpunk theme
- [ ] Test tooltip positioning on all screen sizes
- [ ] Ensure tooltips don't interfere with card click interactions

## Implementation Notes

### CSS Tooltip Styles

```css
/* In _css.py - Add tooltip styles */
[data-tooltip] {
    position: relative;
    cursor: help;
}

[data-tooltip]::before,
[data-tooltip]::after {
    position: absolute;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s ease, transform 0.2s ease;
    z-index: 1000;
}

[data-tooltip]::before {
    content: attr(data-tooltip);
    background: var(--bg-panel);
    border: 1px solid var(--cyan);
    color: var(--text);
    padding: 0.5rem 0.75rem;
    font-size: 0.7rem;
    text-transform: none;
    letter-spacing: 0;
    white-space: nowrap;
    box-shadow: var(--shadow-cyan-medium);
    clip-path: var(--clip-corner-sm);
    transform: translateY(-5px);
}

[data-tooltip]::after {
    content: '';
    width: 0;
    height: 0;
    border: 5px solid transparent;
    border-top-color: var(--cyan);
    transform: translateY(-5px);
}

[data-tooltip]:hover::before,
[data-tooltip]:hover::after,
[data-tooltip]:focus::before,
[data-tooltip]:focus::after {
    opacity: 1;
    transform: translateY(0);
}

/* Positioning variants */
[data-tooltip-position="top"]::before {
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%) translateY(-5px);
}

[data-tooltip-position="top"]::after {
    bottom: calc(100% + 3px);
    left: 50%;
    transform: translateX(-50%) translateY(-5px);
    border-top-color: var(--cyan);
    border-bottom: none;
}

[data-tooltip-position="bottom"]::before {
    top: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%) translateY(5px);
}

[data-tooltip-position="bottom"]::after {
    top: calc(100% + 3px);
    left: 50%;
    transform: translateX(-50%) translateY(5px);
    border-bottom-color: var(--cyan);
    border-top: none;
}
```

### HTML Updates in `_js_core.py`

```javascript
function renderCard(url) {
    // ... existing code ...
    
    return `
        <article class="card${cardClass}" ...>
            <!-- ... existing header ... -->
            <div class="card-metrics" aria-hidden="true">
                <div class="metric">
                    <div class="metric-label" 
                         data-tooltip="HTTP status code returned by the server. 200 = success, 4xx = client error, 5xx = server error"
                         data-tooltip-position="top"
                         aria-label="Status: HTTP response code">
                        Status
                    </div>
                    <div class="metric-value">${statusCode}</div>
                </div>
                <div class="metric" data-latency-state="${latencyState}">
                    <div class="metric-label"
                         data-tooltip="Response time in milliseconds. Green: &lt;200ms, Yellow: 500-1000ms, Red: &gt;1000ms"
                         data-tooltip-position="top"
                         aria-label="Latency: Response time">
                        Latency
                    </div>
                    <div class="metric-value">${formatResponseTimeWithWarning(url.response_time_ms)}</div>
                    <div class="progress-bar" 
                         role="progressbar"
                         data-tooltip="Latency indicator. Scale: 0-2000ms maps to 0-100%"
                         data-tooltip-position="bottom"
                         aria-valuenow="${url.response_time_ms || 0}"
                         aria-valuemin="0" 
                         aria-valuemax="2000"
                         aria-label="Latency indicator">
                        <div class="progress-fill ${latencyClass}" data-width="${latencyPercent}"></div>
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label"
                         data-tooltip="Percentage of successful checks in the last 24 hours"
                         data-tooltip-position="top"
                         aria-label="Uptime: 24-hour success rate">
                        Uptime
                    </div>
                    <div class="metric-value">${formatUptime(url.uptime_24h)}</div>
                    <div class="progress-bar"
                         role="progressbar"
                         data-tooltip="Uptime indicator. 100% = all checks successful, 0% = all checks failed"
                         data-tooltip-position="bottom"
                         aria-valuenow="${uptimePercent}"
                         aria-valuemin="0"
                         aria-valuemax="100"
                         aria-label="Uptime indicator">
                        <div class="progress-fill"
                             data-width="${uptimePercent}"
                             data-color="${uptimeColor}"></div>
                    </div>
                </div>
                <!-- ... rest ... -->
            </div>
        </article>
    `;
}
```

### Enhanced Warning Tooltip

```javascript
function formatResponseTimeWithWarning(ms) {
    if (ms === null || ms === undefined || ms === 0) return '---';
    let prefix = '';
    let tooltip = '';
    if (ms >= 1000) {
        prefix = '<span class="latency-warning-prefix danger" 
                     data-tooltip="High latency warning: Response time exceeds 1000ms threshold"
                     data-tooltip-position="top"
                     aria-label="High latency warning">[!]</span>';
    } else if (ms >= 500) {
        prefix = '<span class="latency-warning-prefix warning"
                     data-tooltip="Elevated latency warning: Response time exceeds 500ms threshold"
                     data-tooltip-position="top"
                     aria-label="Elevated latency warning">[!]</span>';
    }
    return prefix + ms + 'ms';
}
```

### Mobile Considerations

```css
@media (max-width: 600px) {
    /* Disable tooltips on touch devices (use native long-press) */
    @media (hover: none) {
        [data-tooltip]::before,
        [data-tooltip]::after {
            display: none;
        }
    }
    
    /* Keep aria-labels for screen readers */
    [data-tooltip] {
        cursor: default;
    }
}
```

## Expected Impact

- **User education**: Users understand metrics without documentation
- **Accessibility**: Better screen reader support via aria-labels
- **User experience**: Reduced confusion about metric meanings
- **Performance**: Minimal impact (CSS-only, no JavaScript required for basic tooltips)

## Files to Modify

- `webstatuspi/_dashboard/_css.py` - Add tooltip styles
- `webstatuspi/_dashboard/_js_core.py` - Add `data-tooltip` attributes to metric labels

## Dependencies

None

## Progress Log

- **2026-01-25**: Task created based on dashboard design review

## Learnings

- Tooltips improve UX without cluttering the interface
- CSS-only tooltips are performant and accessible
- Mobile devices may need alternative approaches (long-press, aria-labels)
- Tooltips should match the cyberpunk aesthetic for consistency