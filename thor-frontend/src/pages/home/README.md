# Home dashboard layout

Single source of truth for dashboard positioning/layout lives in `Home.css`.

- File: `src/pages/home/Home.css`
- Scope: Page-level positioning only (grid, gaps, placement, spacing, responsive breakpoints)
- Goal: Every widget on the Home dashboard (Global Markets/World Clock, charts, buttons, etc.) is placed by CSS defined here.

## Rules of the road
- Keep page-level layout in `Home.css`.
- Keep widget/component internals in their own scoped styles (e.g., `TimeZone.css`). No page positioning inside component CSS.
- Use the grid container `.dashboard-grid` as the parent layout. Add new sections as `.dashboard-card` (and optional additional class).

## How to add a new widget
1. Add a section in `Home.tsx` under the `.dashboard-grid` container, for example:
   - `<section className="dashboard-card charts" aria-label="Charts">...</section>`
2. Position it in `Home.css` by updating the grid rules:
   - Adjust `.dashboard-grid` columns/rows or define grid areas and assign `grid-area` to the new section class.

## Current layout hooks
- `.dashboard-grid` — main responsive grid for the dashboard
- `.dashboard-card` — shared card styling wrapper for widgets
- `.quick-actions` — optional utility layout class for button rows

## Notes
- The Global Markets widget (`TimeZone.tsx`) has its own `TimeZone.css` for internal table styling only.
- Avoid reintroducing global page padding/margins in component CSS; keep the page flush under the AppBar as configured.
