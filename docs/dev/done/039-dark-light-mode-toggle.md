# Task #039: Dark/Light Mode Toggle

## Metadata
- **Status**: done
- **Priority**: P1
- **Slice**: Dashboard, UX
- **Created**: 2026-01-24
- **Started**: 2026-01-24
- **Completed**: 2026-01-24
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a dashboard user, I want to toggle between dark and light themes so that I can view the dashboard comfortably in different lighting conditions.

**Acceptance Criteria**:
- [x] Toggle button in header with sun/moon icon
- [x] Theme preference stored in `localStorage`
- [x] CSS variables for colors (background, text, cards, borders)
- [x] Respect `prefers-color-scheme` on first visit
- [x] Smooth transition between themes (0.2s)
- [x] All dashboard elements styled for both themes

## Implementation Notes

### Add CSS variables to `_css.py`

```css
:root {
    --bg-primary: #f5f5f5;
    --bg-card: #ffffff;
    --text-primary: #333333;
    --text-secondary: #666666;
    --border-color: #e0e0e0;
}

[data-theme="dark"] {
    --bg-primary: #1a1a1a;
    --bg-card: #2d2d2d;
    --text-primary: #f0f0f0;
    --text-secondary: #b0b0b0;
    --border-color: #404040;
}

body {
    background-color: var(--bg-primary);
    color: var(--text-primary);
    transition: background-color 0.2s, color 0.2s;
}
```

### Add toggle button to header in `_html.py`

```html
<button id="themeToggle" aria-label="Toggle theme">
    <span class="icon-sun">☀️</span>
    <span class="icon-moon">🌙</span>
</button>
```

### Add JS to `_js_core.py`

```javascript
function initTheme() {
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    document.documentElement.dataset.theme = theme;
    updateToggleIcon(theme);
}

function toggleTheme() {
    const current = document.documentElement.dataset.theme;
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem('theme', next);
    updateToggleIcon(next);
}

function updateToggleIcon(theme) {
    document.querySelector('.icon-sun').style.display = theme === 'dark' ? 'inline' : 'none';
    document.querySelector('.icon-moon').style.display = theme === 'light' ? 'inline' : 'none';
}

initTheme();
document.getElementById('themeToggle').addEventListener('click', toggleTheme);
```

## Files to Modify

- `webstatuspi/_dashboard/_css.py` - Add CSS variables and dark theme
- `webstatuspi/_dashboard/_html.py` - Add toggle button
- `webstatuspi/_dashboard/_js_core.py` - Add theme logic

## Dependencies

None

## Progress Log

- **2026-01-24**: Started (parallel execution with task #040)
- **2026-01-24**: Completed implementation
  - Added CSS variables for light theme (default) and dark theme
  - Updated all color references to use CSS variables
  - Added theme toggle button in header with sun/moon icons
  - Implemented `initTheme()`, `toggleTheme()`, and `updateToggleIcon()` functions
  - Theme respects `prefers-color-scheme` on first visit
  - Theme preference saved to `localStorage`
  - Smooth 0.2s transitions between themes
  - All dashboard elements (cards, modals, buttons, charts) styled for both themes
  - Accessible with proper ARIA labels
