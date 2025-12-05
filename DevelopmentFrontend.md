Thor Trading Frontend — Development Guide (Updated)

Overview
This document describes the current (verified) frontend architecture for the Thor Trading platform and replaces earlier duplicated / outdated notes. Drag & drop features have been removed from active code (dependencies remain but are unused). L1 Card system now lives inside page‑specific FutureTrading folders, not under top‑level components.

Environment Profiles (NEW)
- The `thor-frontend` app now includes two env templates:
  - `.env.dev` → local `python manage.py runserver` (http://localhost:8000/api)
  - `.env.docker` → Docker/Gunicorn stack (http://localhost:8001/api)
- Use the helper scripts so Vite always points at the correct backend:
  - `npm run dev:local` copies `.env.dev` into `.env.local` and starts Vite.
  - `npm run dev:docker` copies `.env.docker` into `.env.local` and starts Vite.
  - Standalone copies: `npm run env:local` / `npm run env:docker`.
Vite reads `.env.local` at startup, so these commands eliminate manual edits when switching between dev and Docker backends.

Tech Stack (Current)
React 19
TypeScript 5.8
React Router v7
MUI (Material UI v7)
React Query (@tanstack/react-query)
Axios, date-fns, recharts
Global layout system: AppBar + CollapsibleDrawer + GlobalBanner + HomeRibbon
Modular CSS + single aggregated stylesheet: src/styles/global.css

High-Level Layout
All protected routes (/app/*) are wrapped by AppLayout which itself composes GlobalHeader (AppBar + Drawer), GlobalBanner (always visible under AppBar), scrollable content region, and HomeRibbon (bottom persistent bar). Pages supply content only; layout chrome is centralized.

Route Model
App.tsx defines ONLY routing + feature toggles state. No visual layout code lives there. Certain routes (currently /app/home and /app/futures) are treated as full‑width (no MUI Container). Others render inside a zero‑padding Container to keep consistent spacing.

Feature Toggles Passed Through AppLayout
- Trading Activity panel (showTradingActivity)
- Account Statement panel (showAccountStatement)
- Global Market mini widget visibility (showGlobalMarket)
- Futures on Home dashboard (showFuturesOnHome)
These are managed in App.tsx and exposed to the drawer buttons.

Current Project Structure (Actual)
src/
 ├── App.tsx                  # Routing + toggles (no layout markup)
 ├── main.tsx                 # App bootstrap
 ├── styles/global.css        # Aggregated imports + resets + theme vars
 │
 ├── layouts/
 │    ├── AppLayout.tsx       # Wraps GlobalHeader + Banner + Ribbon + content
 │    └── AuthLayout.tsx      # Auth pages frame
 │
 ├── components/
 │    ├── GlobalHeader.tsx    # AppBar + integrates CollapsibleDrawer
 │    ├── CollapsibleDrawer.tsx
 │    ├── GlobalBanner.tsx
 │    ├── GlobalBanner.css
 │    ├── HomeRibbon.tsx
 │    ├── Grid/
 │    │    ├── TwoByThreeGrid.tsx
 │    │    ├── TwoByThreeGrid.css
 │    │    └── APP_GUIDELINES.md
 │    └── ProtectedRoute.tsx
 │
 ├── pages/
 │    ├── Home/Home.tsx
 │    ├── GlobalMarkets/GlobalMarkets.tsx
 │    ├── FutureTrading/... (FutureHome, RTD, market widgets, L1 card assets)
 │    ├── AccountStatement/AccountStatement.tsx
 │    ├── ActivityPositions/index.tsx (or component file)
 │    └── User/ (Login, Register, User dashboard)
 │
 ├── context/TradingModeContext.tsx
 ├── hooks/ (custom React hooks — future expansion)
 ├── services/ (API clients — axios wrappers etc.)
 ├── types/ (shared TypeScript interfaces)
 ├── theme.ts (MUI theme customization point)
 └── vite-env.d.ts

Removed / Changed vs Prior Doc
- L1Card folder at top level: NOT present; L1 card styles now reside under FutureTrading RTD paths (see global.css imports).
- Drag & drop: Not currently implemented even though @dnd-kit packages remain; no active usage in code inspection.
- GlobalBanner lives directly under components (not nested folder) with matching CSS beside it.
- Added HomeRibbon persistent bottom bar (not previously documented).
- GlobalHeader wraps the AppBar and houses CollapsibleDrawer instead of a separate AppBar component and standalone Drawer documentation.

Core Components
1. App.tsx
Responsibilities: defines protected vs auth routes, supplies toggle state, selects full‑width vs container layouts. Never includes visual layout other than <Routes>. Redirects root → /app/home.

2. AppLayout.tsx
Pure layout composition. Accepts toggle props and renders:
- <GlobalHeader> (AppBar + CollapsibleDrawer + trading mode indicator)
- <GlobalBanner> (connection/account info + tab navigation)
- Scrollable content region (.app-content-scroll)
- <HomeRibbon> bottom bar

3. GlobalHeader.tsx
Renders fixed AppBar with title and trading mode Chip, and the CollapsibleDrawer. Manages internal drawer open/close state. Sets top margin so content sits below AppBar.

4. CollapsibleDrawer.tsx
Permanent MUI Drawer with toggle button, account info (when open), navigation links, and buttons that trigger feature visibility toggles. Sign out clears tokens and navigates to /auth/login.

5. GlobalBanner.tsx
Always visible below AppBar. Provides: connection indicator, account ID, quick links (email, messages, support, chat, setup), summary balances row, and tab navigation (Home, Futures, Global, Account, Activity, Research placeholder, Settings placeholder). Styling isolated in GlobalBanner.css.

6. TwoByThreeGrid.tsx
Standard 2×3 dashboard grid. Accepts an array of tile config objects (id, title, slotLabel, hint, children). Automatically pads missing tiles with empties up to six. Each tile has header (title + slot label) and scrollable body region. Grid CSS centralizes layout; tiles SHOULD NOT self-resize the overall grid.

7. HomeRibbon.tsx
Persistent footer/ribbon (implementation details in component). Keep styles separate in HomeRibbon.css. Avoid page CSS interfering with its position.

Styling Strategy
Single aggregation file: styles/global.css imports ALL component and page CSS. Provides resets, theme variables (CSS custom properties), utility classes, dark canvas definitions, and overrides for MUI default colors to enforce dark theme.
Per-component CSS: Local appearance only (e.g., GlobalBanner.css, TwoByThreeGrid.css). Page CSS (Home.css, GlobalMarkets.css, etc.) strictly for page-specific layout adjustments, never global chrome.
Utility classes (flex, spacing, etc.) are defined in global.css for consistency.

Scrolling & Layout Rules
- Only .app-content-scroll region scrolls between Banner and Ribbon.
- Tiles inside TwoByThreeGrid use internal overflow-y for large content.
- Avoid setting min-height:100vh on nested containers (removed to prevent content push off-screen).
- Home page and futures dashboard designated full‑width (no Container wrapper) — adjust via isFullWidth check in App.tsx.

Development Rules
1. Do NOT place layout logic in page components. Pages compose widgets (e.g., <TwoByThreeGrid />) and supply data/tile config only.
2. Component CSS must not resize global containers or alter fixed layout heights (AppBar, Banner, Ribbon).
3. Internal scrolling only: large widgets scroll within their tile; never expand grid.
4. GlobalBanner styles belong exclusively in GlobalBanner.css — no page CSS may target its selectors.
5. Always-visible chrome lives in AppLayout (GlobalHeader, Drawer, Banner, Ribbon).
6. Feature toggles route through AppLayout props; if adding a new persistent toggle button, integrate in CollapsibleDrawer and mirror state in App.tsx.
7. Drag & Drop: currently disabled; when reinstated, isolate DnD logic inside a dedicated widget folder (components/DnD/*) and avoid coupling with grid layout CSS.

Adding a New Dashboard/Home Variant
1. Create page folder (e.g., src/pages/FutureTrading/Home/FutureHome.tsx).
2. Define const TILES: DashboardTile[] with id/title/children/hint.
3. Render <TwoByThreeGrid tiles={TILES} /> inside a wrapper div with page-specific className.
4. Add page stylesheet; import automatically via global.css (append an @import line).
5. If needs full‑width layout, add path to fullWidthRoutes array in App.tsx.

Example Tile Config (Futures Home)
const FUTURES_TILES: DashboardTile[] = [
  { id: 'global', title: 'Global Market', children: <GlobalMarkets /> },
  { id: 'l1', title: 'L1 Cards', hint: 'Realtime futures quotes' },
  { id: 'orders', title: 'Open Orders', hint: 'Working & filled' },
  { id: 'positions', title: 'Positions', hint: 'Current holdings' },
  { id: 'risk', title: 'Risk Monitor', hint: 'Exposure metrics' },
  { id: 'system', title: 'System Status', hint: 'Feeds / jobs' },
];
return <TwoByThreeGrid tiles={FUTURES_TILES} />;

Recommended Workflow
- Add widget: create under components/ or page subfolder; supply via tile children.
- Add page: create folder, implement grid tiles, add route in App.tsx.
- Add global chrome element: modify AppLayout (rare) & import CSS in global.css.
- Update theme or global resets: edit styles/global.css only.

Drag & Drop Hook
- Location: `src/hooks/DragAndDrop.ts` exporting `useDragAndDropTiles`.
- Purpose: centralizes the drag-and-drop tile order logic (state + optional `localStorage` persistence) so every dashboard uses the same behavior.
- Usage pattern for any 2×3 “home” page:
  1. Define `const BASE_TILES: DashboardTile[] = [...]`.
  2. Call `const { tiles, setTiles, resetTiles } = useDragAndDropTiles(BASE_TILES, { storageKey: 'thor.somepage.tiles' });`.
  3. Render `<TwoByThreeGridSortable tiles={tiles} onReorder={setTiles} />` inside the page layout.
  4. (Optional) expose `resetTiles` via a button/menu if users should restore defaults.
- Current adopters: `src/pages/Home/Home.tsx` and `src/pages/FutureTrading/Home/FutureHome.tsx`.
- When building a new home page, repeat the pattern above with a unique storage key to get drag/drop + scroll with zero copy/paste.

Future / TODO
- Remove unused @dnd-kit dependencies if drag & drop remains inactive.
- Centralize balance + account data into context/provider (currently hard-coded strings in GlobalBanner / Drawer).
- Extract drawer account metrics into a reusable AccountMetrics component.
- Replace placeholder Research / Settings tabs with real pages.
- Consider dynamic tile registration for user personalization (when DnD returns).

Summary
The current architecture centralizes global chrome, isolates page content, and enforces consistent grid behavior. It minimizes CSS bleed, provides clear extension points (new pages, new tiles, new toggles), and is ready for incremental enhancement (widgets, personalization, DnD reintroduction) without structural rewrite.

This document is now aligned with the actual source tree and implementation as of the latest Dev branch.

Last Verified: 2025-12-01

🚀 Overview

This document explains the internal structure, rules, and development flow of the Thor Trading Frontend.

The app is built with:

React 18

TypeScript

React Router v6

Material-UI (MUI)

Custom global layout (AppBar + Drawer + GlobalBanner)

Modular CSS (per-component + global)

All /app/* pages share the same top-level layout and global banner.

The Home pages (Home, Futures Home, Account Home, etc.) all use the same standard 2×3 tile grid, implemented as a shared component.

📁 Project Structure
src/
 ├── App.tsx                   # Top-level routing
 ├── global.css                # Global styles + imports
 │
 ├── layouts/
 │    ├── AppLayout.tsx        # Drawer + AppBar + GlobalBanner wrapper
 │    └── AuthLayout.tsx
 │
 ├── components/
 │    ├── GlobalBanner/
 │    │      ├── GlobalBanner.tsx
 │    │      └── GlobalBanner.css
 │    │
 │    ├── Grid2x3/
 │    │      ├── TwoByThreeGrid.tsx
 │    │      └── TwoByThreeGrid.css
 │    │
 │    ├── L1Card/              # L1 Trading Cards System
 │    │      ├── L1Card.tsx
 │    │      ├── L1Card.css
 │    │      ├── L1Header.tsx
 │    │      ├── L1BidAsk.tsx
 │    │      ├── L1QtyPanel.tsx
 │    │      ├── L1MetricsGrid.tsx
 │    │      └── shared.ts
 │    │
 │    └── ...other reusable components
 │
 ├── pages/
 │    ├── Home/
 │    │     ├── Home.tsx
 │    │     └── Home.css
 │    │
 │    ├── GlobalMarkets/
 │    │     ├── GlobalMarkets.tsx
 │    │     └── GlobalMarkets.css
 │    │
 │    ├── FutureTrading/
 │    │     ├── FutureRTD.tsx
 │    │     ├── MarketDashboard.tsx (if used)
 │    │     └── ...RTD widget CSS
 │    │
 │    ├── AccountStatement/
 │    ├── ActivityPositions/
 │    └── User/
 │
 └── context/
      └── TradingModeContext.tsx

⭐ Core Architecture
1. App.tsx — Routing

App.tsx controls route structure only, nothing visual.

Responsibilities:

Routing between public (/auth/*) and protected (/app/*) routes

Wrapping protected routes in AppLayout

Passing toggle props for features (Global Market toggle, Futures toggle, etc.)

Never put UI layout inside App.tsx.

2. AppLayout.tsx — Global Layout

This component controls the entire UI frame:

CollapsibleDrawer (left)

AppBar / GlobalHeader (top)

GlobalBanner (below AppBar)

<main> content region (scrollable)

Every page under /app/* shows inside this layout.

3. GlobalBanner.tsx — Always-Displayed Banner

Purpose:

Displays connection status

Account ID

Email + Quick Links

Balances

Tab Navigation (Home, Futures, Global, Activity, etc.)

It lives outside page content, so it appears on every subpage.

All its styles live in:

src/components/GlobalBanner/GlobalBanner.css


Nothing inside Home.css should affect it.

4. Standard Home Grid — 2 × 3 Tiles

Every Home page follows the same structure using:

src/components/Grid2x3/TwoByThreeGrid.tsx
src/components/Grid2x3/TwoByThreeGrid.css


Features:

2 columns

3 rows

Fixed layout

Scrollable internal tile bodies

Tile structure:

Header

Slot label

Body content (widgets, L1 cards, watchlists, heat maps, etc.)

All grid styling is centralized.

5. Tile Widgets (Inside Each Grid Cell)

Examples:

Global Market (mini version)

Futures L1 Cards grid (2 columns × many rows, scrollable)

Watchlists

News Streaming

P/L Open summary

Heat Maps

Widgets should:

Fit inside the tile

Scroll internally (not resize the tile)

Never modify the page layout

6. CSS Structure
global.css

Imports all component/page CSS

Defines global resets

Defines theme variables

Should not style individual widgets

Component CSS (preferred)

Each component has its own CSS:

GlobalBanner.css
TwoByThreeGrid.css
L1Card.css
GlobalMarkets.css

Thor Frontend CSS Guide

This guide explains where styles go, how to name things, and what NOT to do, based on your current React setup:

global.css

page CSS like Home.css, GlobalMarkets.css

component CSS like GlobalBanner.css, TwoByThreeGrid.css, L1Card.css

The goal: predictable layout, no mystery spacing, and easy-to-find styles.

1. CSS Layers (Who Owns What?)

We have 3 main layers:

1️⃣ Global Layer — global.css

Purpose

Resets (*, html, body, #root)

Theme variables (:root – colors, spacing, fonts)

Global utilities (.flex, .rounded, etc.)

High-level app canvas styles (main, .dashboard-canvas)

Rules

✅ OK: global element rules (html, body, h1–h6, main)

✅ OK: utility classes (.flex, .text-center)

❌ NOT OK: page-specific stuff like .home-top-strip, .global-banner-tabs

❌ NOT OK: widget-specific styles like .l1-price, .tbt-tile

Think of global.css as “theme + utilities”, not “dump everything here.”

2️⃣ Component Layer — component CSS files

Examples:

components/GlobalBanner/GlobalBanner.css

components/Grid2x3/TwoByThreeGrid.css

components/L1Card/L1Card.css

components/CollapsibleDrawer.css

Purpose

Styles that belong to a reusable building block.

If the component can be used in multiple pages, its CSS belongs with it.

Rules

Name classes after the component, short prefix:

GlobalBanner → .global-banner-*, can reuse .home-* where you intentionally mirror home look

TwoByThreeGrid → .tbt-*

L1Card → .l1-card-*

All layout for that component lives in its own CSS file.

Components may not resize outer layout (no messing with main, .home-screen, etc.)

3️⃣ Page Layer — page CSS files

Examples:

pages/Home/Home.css

pages/GlobalMarkets/GlobalMarkets.css

pages/FutureTrading/FutureRTD/FutureRTD.css

Purpose

Page-specific layout and spacing.

How the page uses the global layout + components together.

Rules

Use for: .home-screen, tile spacing on that page, page-specific grid tweaks.

Don’t redefine component internals here (don’t restyle .tbt-header inside Home.css).

Don’t change positions of global elements (AppBar, Drawer, GlobalBanner) – that’s layout / component layer.

2. Naming Conventions
Prefix by feature

To avoid collisions:

Home page: .home-*

Global banner: .global-banner-* (and some .home-* reused intentionally)

2×3 grid (TwoByThreeGrid): .tbt-*

L1Card system: .l1-card-*, .l1-header-*, .l1-metrics-*

Drawer: .thor-drawer, .thor-nav-*

Example
/* Good */
.home-tile-body { ... }
.tbt-grid { ... }
.l1-card-root { ... }

/* Avoid generic like this */
.card { ... }       /* too generic */
.header { ... }     /* will collide somewhere */
.grid { ... }       /* you already have many grids */

3. Layout Rules
3.1. Global layout

AppLayout controls:

Drawer width (CollapsibleDrawer.css)

Header height

Main content scroll (main / [role="main"])

Rules

Don’t override main or [role="main"] in page CSS.

Let AppLayout own padding and top offset under the AppBar.

3.2. GlobalBanner layout

GlobalBanner.tsx + GlobalBanner.css:

Lives directly under the AppBar.

Always visible across pages.

Contains:

Connection row

Balances row

Tabs row

Rules

All .home-connection, .home-contact-link, .home-nav-button, etc., styles belong in GlobalBanner.css (not Home.css).

Banner height and look must not be changed by page CSS.

3.3. Home “canvas” layout

Home page (Home.tsx + Home.css) has:

The global banner above it

A main content region with:

2×3 grid (TwoByThreeGrid)

Bottom ticker ribbon (HomeRibbon)

Rules

.home-screen controls full-screen black background and flex column.

.home-content controls padding and overall canvas area (below banner).

Do not change global header/drawer spacing here.

All contained widgets must fit inside the content area.

3.4. 2×3 grid layout (TwoByThreeGrid)

TwoByThreeGrid.css should fully control:

.tbt-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;  /* 2 columns */
  grid-auto-rows: 1fr;             /* fixed rows */
  gap: 12px;
  width: 100%;
  height: 100%;
}

.tbt-tile {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.tbt-body {
  flex: 1;
  overflow: auto;  /* scroll inside tile */
}


Key rule:
📌 Tiles can scroll inside themselves, but the tile size doesn’t change.

4. Scroll Behavior

To avoid the “home is resizing everything” problem:

The outer canvas (main, .home-content) should:

overflow: hidden or overflow-y: auto once.

The grid tiles (.tbt-tile) have:

overflow: hidden on tile

overflow-y: auto on inner body .tbt-body

What you want:

Screen height: controlled by AppLayout.

Scrolling:

Vertical: page or tile, not both at same time.

Horizontal: only where explicitly requested (e.g., futures strip).

5. MUI Overrides

You already have a few MUI overrides in global.css:

.MuiTypography-root {
  color: white !important;
}

.MuiPaper-root {
  background-color: rgba(255, 255, 255, 0.1) !important;
  color: white !important;
}


Rules for MUI overrides:

Keep them in global.css or a dedicated mui-overrides.css.

Use !important only when necessary to fight default MUI styles.

Prefer targeting specific variants when possible:

.MuiDrawer-paper.thor-drawer-paper { ... }


instead of overriding .MuiDrawer-paper everywhere.

6. Working With New Components

When you add a new UI piece, decide:

Is this reusable across pages?
Or is it only for this one page?

If reusable (widget / building block)

Create src/components/MyWidget/MyWidget.tsx

Create src/components/MyWidget/MyWidget.css

Import the CSS in the component or via global.css

Example

import "./MyWidget.css";

export const MyWidget = () => (
  <div className="my-widget-root">
    ...
  </div>
);

.my-widget-root { ... }
.my-widget-header { ... }
.my-widget-body { ... }

If page-only

Add styles to that page’s CSS, e.g. Home.css:

.home-special-panel, .home-sidebar, etc.

Don’t define global-ish class names here.

7. Do / Don’t Cheat Sheet
✅ DO

✅ Use component CSS for component internals.

✅ Use page CSS for page layout only.

✅ Keep GlobalBanner styles only in GlobalBanner.css.

✅ Let grid components own their own sizing (TwoByThreeGrid.css).

✅ Make tiles scrollable internally when content is tall.

❌ DON’T

❌ Don’t put home-* styling in both Home.css and GlobalBanner.css.

❌ Don’t let a widget change the width of .home-screen or main.

❌ Don’t use generic classnames (.card, .header) for big UI pieces.

❌ Don’t rely on random !important unless fighting MUI defaults.

If you want, next we can:

Write a small LAYOUT.md that diagrams:

AppBar → GlobalBanner → Home canvas → Grid → Widgets

Write a WIDGETS.md that lists:

Global Market

L1 Cards

P/L Open

Watchlist

Ribbon
and describes what each one’s CSS hooks are.