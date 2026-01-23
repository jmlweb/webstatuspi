# Task #042: Status Badge SVG Endpoint

## Metadata
- **Status**: completed
- **Priority**: P1 - Active
- **Slice**: Backend, API
- **Created**: 2026-01-24
- **Started**: 2026-01-24
- **Completed**: 2026-01-24
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user, I want to embed a status badge in my website or README so that visitors can see the current system status.

**Acceptance Criteria**:
- [x] Endpoint `GET /badge.svg` returns valid SVG image
- [x] Query param `?url=NAME` for specific service status
- [x] Without param, show overall system status
- [x] Badge colors: green (UP), red (DOWN), yellow (degraded), gray (unknown)
- [x] Proper Content-Type header (`image/svg+xml`)
- [x] Cache-Control header for CDN caching (max-age=60)

## Implementation Notes

### Add endpoint to `api.py`

```python
@app.get("/badge.svg")
async def status_badge(url: str = None):
    if url:
        status = get_status_by_name(url)
        label = url
        state = status["status"] if status else "unknown"
    else:
        statuses = get_all_statuses()
        up = sum(1 for s in statuses if s["status"] == "UP")
        total = len(statuses)
        label = "status"
        state = "up" if up == total else ("down" if up == 0 else "degraded")

    svg = generate_badge_svg(label, state)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=60"}
    )
```

### SVG template

```python
def generate_badge_svg(label: str, state: str) -> str:
    colors = {
        "up": "#4c1",      # green
        "down": "#e05d44", # red
        "degraded": "#dfb317",  # yellow
        "unknown": "#9f9f9f"   # gray
    }
    color = colors.get(state.lower(), colors["unknown"])
    text = state.upper()

    # Shields.io style badge
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="90" height="20">
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <mask id="a"><rect width="90" height="20" rx="3" fill="#fff"/></mask>
  <g mask="url(#a)">
    <rect width="45" height="20" fill="#555"/>
    <rect x="45" width="45" height="20" fill="{color}"/>
    <rect width="90" height="20" fill="url(#b)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,sans-serif" font-size="11">
    <text x="22.5" y="15" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="22.5" y="14">{label}</text>
    <text x="67.5" y="15" fill="#010101" fill-opacity=".3">{text}</text>
    <text x="67.5" y="14">{text}</text>
  </g>
</svg>'''
```

### Usage in README

```markdown
![Status](https://status.example.com/badge.svg)
![API Status](https://status.example.com/badge.svg?url=API_PROD)
```

## Files to Modify

- `webstatuspi/api.py` - Add /badge.svg endpoint

## Dependencies

None (SVG is plain text/XML)

## Progress Log

- [2026-01-24 14:00] Started task
- [2026-01-24 14:15] Implemented badge endpoint:
  - Added `_generate_badge_svg()` function to generate shields.io-style SVG badges
  - Added `_send_svg()` method to send SVG responses with proper headers
  - Added `_handle_badge()` method to handle both overall and per-service status
  - Added route handling for `/badge.svg` and `/badge.svg?url=NAME` query param
  - All acceptance criteria met
- [2026-01-24 14:16] Completed implementation, ready for commit
- [2026-01-24 14:18] Task completed - all acceptance criteria met
