# Task #052: Improve Metric Spacing and Layout

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: Dashboard, Frontend
- **Created**: 2026-01-25
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a dashboard user, I want better spacing between metrics so the information is easier to scan and read without visual clutter.

**Acceptance Criteria**:
- [ ] Increase gap between metric boxes from 12px to 16px
- [ ] Improve padding inside metric boxes for better readability
- [ ] Ensure spacing is consistent across all card states
- [ ] Maintain responsive behavior on mobile devices
- [ ] Verify no layout shifts occur during updates
- [ ] Test with various numbers of URLs (1-10 cards)

## Implementation Notes

### CSS Grid Gap Increase

```css
/* In _css.py - Update grid gap */
:root {
    /* ... existing vars ... */
    --gap: 16px;  /* Increased from 12px */
}

.card-metrics {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--gap);  /* Now 16px instead of 12px */
}

.stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--gap);  /* Consistent spacing */
    margin-top: var(--gap);  /* Increased from 12px */
}
```

### Metric Padding Enhancement

```css
.metric {
    text-align: left;
    padding: 12px;  /* Increased from 10px */
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 6px;  /* Increased from 4px for better label/value separation */
}

.mini-stat {
    background: rgba(0, 0, 0, 0.2);
    padding: 10px 12px;  /* Increased horizontal padding */
    border: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 6px;  /* Increased from 4px */
    text-align: left;
}
```

### Card Internal Spacing

```css
.card-header {
    display: flex;
    justify-content: flex-start;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1.25rem;  /* Increased from 1rem */
    padding-bottom: 1rem;  /* Increased from 0.75rem */
    border-bottom: 1px solid var(--border);
}

.card-footer {
    margin-top: 0.75rem;  /* Increased from 0.5rem */
    padding-top: 0.75rem;  /* Increased from 0.5rem */
    border-top: 1px solid var(--border);
}
```

### Responsive Adjustments

```css
@media (max-width: 600px) {
    :root {
        --gap: 10px;  /* Slightly smaller on mobile to fit content */
    }
    
    .card-metrics {
        grid-template-columns: repeat(2, 1fr);
        gap: var(--gap);
    }
    
    .metric {
        padding: 10px;  /* Slightly less padding on mobile */
    }
}
```

## Expected Impact

- **Readability**: 33% more space between metrics (12px → 16px)
- **Visual hierarchy**: Better separation of metric groups
- **User experience**: Easier scanning of information
- **Performance**: Zero impact (CSS-only changes)

## Files to Modify

- `webstatuspi/_dashboard/_css.py` - Update spacing variables and metric styles

## Dependencies

None

## Progress Log

- **2026-01-25**: Task created based on dashboard design review

## Learnings

- Adequate spacing reduces cognitive load when scanning multiple metrics
- Consistent spacing creates visual rhythm and improves readability
- Mobile devices may need slightly tighter spacing to fit content