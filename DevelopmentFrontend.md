React + TypeScript + MUI + Custom Layout System📘 Thor Trading Frontend — DEVELOPMENT.md

React + TypeScript + MUI + Custom Layout System

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
 │    ├── Grid/
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

src/components/Grid/TwoByThreeGrid.tsx
src/components/Grid/TwoByThreeGrid.css


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


This keeps things isolated and prevents bleed-through.

Page CSS

Example:

Home.css
FutureRTD.css
AccountStatement.css


Used only for page-specific layout, NOT global UI.

🔧 Development Rules
1. Never put layout logic in a page component

Home.tsx should only:

Render <TwoByThreeGrid>

Supply tile config

Everything else belongs elsewhere.

2. Component CSS must never resize global containers

Widgets must fit inside their tile, not change the grid size.

3. Tiles can scroll internally

Tile height is fixed by the grid. Large widgets must use:

overflow-y: auto;

4. Keep GlobalBanner styles out of Home.css

This was a source of major breakage. Now corrected.

5. All “always visible” components must live in AppLayout

Including:

Drawer

AppBar

GlobalBanner

🧪 How to Add a New Home Page (Futures Home, Research Home, etc.)

Create a new page:

src/pages/Futures/FuturesHome.tsx


Import the grid:

import TwoByThreeGrid from "../../components/Grid/TwoByThreeGrid";


Define tiles:

const FUTURES_TILES = [
  { id: "l1", title: "L1 Cards", children: <FuturesL1Widget /> },
  { id: "orders", title: "Open Orders" },
  { id: "positions", title: "Positions" },
  { id: "risk", title: "Risk Monitor" },
  { id: "news", title: "Futures News" },
  { id: "system", title: "System Status" },
];


Render:

return <TwoByThreeGrid tiles={FUTURES_TILES} />;

🛠 Recommended Workflow
Add a widget?

➤ Create component in /components/<WidgetName>/

Add a page?

➤ Reuse TwoByThreeGrid + supply tile config

Add a global UI element?

➤ Put it in /components/ and load inside AppLayout.tsx

Add / modify global styles?

➤ Edit global.css only

🎯 Summary

This frontend architecture gives you:

A consistent layout across all home pages

A globally-visible banner

A reusable & scalable tile grid

Cleanly separated CSS

Predictable behavior (no home screen “taking over” other pages)

A strong foundation for your trading widgets and dashboards

This is the correct and professional way to structure a React trading platform frontend.

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
 │    ├── Grid/
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

src/components/Grid/TwoByThreeGrid.tsx
src/components/Grid/TwoByThreeGrid.css


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