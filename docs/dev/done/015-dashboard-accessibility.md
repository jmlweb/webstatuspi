# Task #015: Dashboard Accessibility

## Metadata
- **Status**: completed
- **Priority**: P1
- **Slice**: API
- **Created**: 2026-01-21
- **Started**: 2026-01-21
- **Completed**: 2026-01-21
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user with accessibility needs, I want comprehensive accessibility support (screen readers, WCAG compliance, keyboard navigation) so that I can effectively use the dashboard regardless of my abilities.

**Acceptance Criteria**:
- [x] Semantic HTML structure with proper heading hierarchy (h1, h2, etc.) and landmark regions (header, main, nav, etc.)
- [x] ARIA labels and roles added to all interactive elements (buttons, modals, cards, status indicators)
- [x] Full keyboard navigation support with visible focus states and logical tab order
- [x] Color contrast meets WCAG 2.1 AA standards (4.5:1 for text, 3:1 for UI components)
- [x] Screen reader announces status changes and live data updates appropriately
- [x] Modal dialogs trap focus and can be closed with Escape key
- [x] All interactive elements have accessible names and states

## Implementation Notes

The dashboard currently has good visual design but lacks accessibility features:

### Current State
- Static HTML embedded in `_dashboard.py`
- No semantic HTML structure (divs everywhere)
- No ARIA labels or roles
- Focus states exist but may not meet contrast requirements
- Modal click-outside and ESC closing exist (good foundation)
- Keyboard navigation partially works but not comprehensive

### Required Changes

1. **Semantic HTML** (`_dashboard.py:9-1294`)
   - Convert divs to semantic elements (header ✓, main ✓, section, article)
   - Add proper heading hierarchy
   - Add landmark regions with ARIA roles

2. **ARIA Labels/Roles**
   - Add `role="status"` or `aria-live="polite"` to live indicator and summary bar
   - Add `aria-label` to status indicators, progress bars, and metric values
   - Add `role="dialog"` and `aria-modal="true"` to modals
   - Add `aria-labelledby` and `aria-describedby` to modal content

3. **Keyboard Navigation**
   - Ensure tab order is logical (header → summary → cards → modal)
   - Add visible focus indicators that meet contrast requirements
   - Make cards keyboard-activatable (currently only click-to-open)
   - Add keyboard shortcuts (optional): `?` for help, `/` for search

4. **Focus Management**
   - Trap focus within modals when open
   - Return focus to trigger element when modal closes
   - Skip link for keyboard users to jump to main content

5. **Color Contrast**
   - Audit CSS variables against WCAG AA standards
   - Ensure text on backgrounds meets 4.5:1 ratio
   - Ensure UI elements (borders, indicators) meet 3:1 ratio

## Files to Modify
- `webstatuspi/_dashboard.py` - Update HTML template with semantic structure and ARIA attributes
- (Possibly) Create `webstatuspi/static/a11y.js` - If focus trap logic becomes complex

## Dependencies
None

## Progress Log
- [2026-01-21 00:00] Started task
- [2026-01-21 00:15] Added skip link for keyboard users
- [2026-01-21 00:15] Added enhanced focus styles with :focus-visible
- [2026-01-21 00:15] Improved color contrast (#606080 → #9090a8)
- [2026-01-21 00:15] Added .sr-only utility class
- [2026-01-21 00:20] Added semantic HTML (header role, nav, article, section, footer)
- [2026-01-21 00:20] Added aria-live regions to summary counts and live indicator
- [2026-01-21 00:25] Added ARIA attributes to modals (role=dialog, aria-modal, aria-labelledby)
- [2026-01-21 00:30] Made cards keyboard accessible (tabindex=0, role=button, keydown handler)
- [2026-01-21 00:30] Added comprehensive aria-labels to cards with status info
- [2026-01-21 00:35] Added focus trapping for both modals
- [2026-01-21 00:35] Added focus return to trigger element on modal close
- [2026-01-21 00:40] Added screen reader announcements for reset operation
- [2026-01-21] Task completed - all acceptance criteria met

## Learnings
- Use `role="button"` with `tabindex="0"` and keyboard handlers for clickable non-button elements
- `aria-live="polite"` is ideal for status updates that shouldn't interrupt users
- Focus trapping in modals requires tracking both first/last focusable elements
- `role="alertdialog"` is more appropriate than `role="dialog"` for confirmation modals
- `:focus-visible` provides better UX than `:focus` (no outline on mouse clicks)
- Color contrast of #606080 on dark backgrounds is insufficient - #9090a8 provides better accessibility
