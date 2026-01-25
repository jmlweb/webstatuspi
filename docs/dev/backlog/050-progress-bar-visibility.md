# Task #050: Improve Progress Bar Visibility

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: Dashboard, Frontend
- **Created**: 2026-01-25
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a dashboard user, I want progress bars to be more visible and easier to read at a glance so I can quickly assess latency and uptime metrics.

**Acceptance Criteria**:
- [ ] Increase progress bar height from 3px to at least 5px
- [ ] Improve contrast between progress fill and background
- [ ] Ensure progress bars are clearly visible on all card states (up/down)
- [ ] Maintain accessibility (ARIA labels remain functional)
- [ ] Test on mobile devices (touch targets remain adequate)
- [ ] Verify performance impact is minimal (CSS-only changes)

## Implementation Notes

### CSS Changes in `_css.py`

```css
/* Current: height: 3px; */
.progress-bar {
    height: 5px;  /* Increased from 3px */
    margin-top: 0.4rem;
    background: rgba(0, 0, 0, 0.5);  /* Darker background for better contrast */
    position: relative;
    overflow: hidden;
    border: 1px solid var(--border);  /* Optional: subtle border for definition */
}

.progress-fill {
    --progress-color: var(--cyan);
    height: 100%;
    width: var(--progress-width, 0%);
    background: repeating-linear-gradient(
        90deg,
        var(--progress-color) 0px,
        var(--progress-color) 4px,
        transparent 4px,
        transparent 6px
    );
    box-shadow: 0 0 8px var(--progress-color);  /* Stronger glow */
    transition: width 0.5s ease;
    border-radius: 1px;  /* Subtle rounding */
}
```

### Responsive Considerations

```css
@media (max-width: 600px) {
    .progress-bar {
        height: 6px;  /* Slightly larger on mobile for touch visibility */
    }
}
```

## Expected Impact

- **Visual clarity**: Progress bars 67% larger (3px → 5px)
- **Accessibility**: Better visibility for users with visual impairments
- **User experience**: Faster metric scanning without reading numbers
- **Performance**: Zero impact (CSS-only changes)

## Files to Modify

- `webstatuspi/_dashboard/_css.py` - Update `.progress-bar` and `.progress-fill` styles

## Dependencies

None

## Progress Log

- **2026-01-25**: Task created based on dashboard design review

## Learnings

- Progress bar visibility is critical for at-a-glance status assessment
- Larger bars improve UX without sacrificing the cyberpunk aesthetic