# Task #038: Resource Hints for API Prefetching

## Metadata
- **Status**: pending
- **Priority**: P3
- **Slice**: Dashboard, WPO
- **Created**: 2026-01-23
- **Started**: -
- **Completed**: -
- **Blocked by**: 034

## Vertical Slice Definition

**User Story**: As a dashboard user, I want the browser to prefetch API endpoints when I hover over cards so that DNS resolution and connection setup happen before I click.

**Acceptance Criteria**:
- [ ] Add `<link rel="prefetch">` hints on card hover
- [ ] Avoid duplicate hints for the same URL
- [ ] Hints point to `/status/<name>` and `/history/<name>` endpoints

## Implementation Notes

### Add to hover handler in `_js_core.py`

```javascript
function addPrefetchHint(urlName) {
    const encoded = encodeURIComponent(urlName);
    if (document.querySelector(`link[href*="${encoded}"]`)) return;

    const statusLink = document.createElement('link');
    statusLink.rel = 'prefetch';
    statusLink.href = '/status/' + encoded;
    statusLink.as = 'fetch';
    document.head.appendChild(statusLink);

    const historyLink = document.createElement('link');
    historyLink.rel = 'prefetch';
    historyLink.href = '/history/' + encoded;
    historyLink.as = 'fetch';
    document.head.appendChild(historyLink);
}
```

### Integrate with hover/touch listeners

Call `addPrefetchHint(urlName)` alongside `prefetchModalData(urlName)` in the event handlers from Task #034.

## Expected Impact

- **DNS lookup time**: Eliminated (0ms vs. 20-100ms)
- **Connection setup**: Overlapped with user interaction

## Files to Modify

- `webstatuspi/_dashboard/_js_core.py` - Add `addPrefetchHint()` function and integrate with hover handlers

## Dependencies

- Task #034 (Modal Prefetch on Hover) - shares the same event listeners

## Progress Log

(empty)

## Learnings

(empty)
