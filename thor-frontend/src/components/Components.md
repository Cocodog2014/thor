# ThorTrading Components Overview

This document describes the core layout and dashboard components used in the ThorTrading front-end.

- **Layout / Shell**
  - `Header/GlobalHeader`
  - `Drawer/CollapsibleDrawer`
  - `Banners/GlobalBanner`
  - `ProtectedRoute`
- **Dashboard Grids**
  - `TwoByThreeGrid` / `TwoByThreeGridSortable`
  - `TwoByTwoGrid` / `TwoByTwoGridSortable`
- **Ribbons**
  - `FooterRibbon`
- **Guidelines**
  - `APP_GUIDELINES.md` (how apps should behave inside grid tiles)

---

## 1. Layout & Shell Components

### 1.1 `GlobalHeader`

**Files**

- `Header/GlobalHeader.tsx`
- `Header/GlobalHeader.css`

Both live in `src/components/Header/` to keep shell assets grouped.

**Role**

The `GlobalHeader` component is the **top-level app shell**:

- Renders the **MUI AppBar** with the “ThorTrading” title.
- Hosts provider/data-source buttons (e.g. `"Connected to: Paper Engine"` buttons).
- Wraps the entire page layout: AppBar + left navigation (drawer) + main content.

**Key responsibilities**

- Provides the fixed **blue gradient app bar** at the top of the screen.
- Manages layout margin/padding so content appears below the AppBar.
- Integrates the `Drawer/CollapsibleDrawer` component on the left.
- Renders `children` as the main page content, typically:
  - `GlobalBanner` (under the AppBar)
  - Page body content (grids, charts, detail views, etc.).

**Styling**

- Uses `.global-header-appbar` for the gradient AppBar background and transitions.
- Uses `.main-content` (`.full-width` or `.with-padding`) for the main content spacing.
- `.header-title` defines the large “ThorTrading” title styling (Cinzel font, gold/glow shadow).

---

### 1.2 `CollapsibleDrawer`

**Files**

- `Drawer/CollapsibleDrawer.tsx`
- `Drawer/CollapsibleDrawer.css`

Located under `src/components/Drawer/` to keep drawer-specific assets grouped.

**Role**

The `CollapsibleDrawer` is the **left-side navigation panel**:

- Provides a collapsible sidebar (open/closed widths).
- Used for routing between major app areas (e.g. Home, Trade, Futures, Settings).
- Meant to feel like a trading terminal / platform left nav.

**Key responsibilities**

- Tracks open/closed state internally (or via props, depending on current implementation).
- Displays navigation items (icons + labels).
- Integrates with `react-router-dom` for navigation via `<Link>` / `useNavigate`.
- Resizes the main content accordingly when expanded or collapsed.

**Styling**

- `.drawer-open` / `.drawer-closed` (or similar) determine width and transition.
- Uses flexbox layout to stack icons/text vertically.
- Background matches the overall dark theme.

**Usage**

`GlobalHeader` typically uses `CollapsibleDrawer` like:

```tsx
<GlobalHeader>
  <CollapsibleDrawer />
  {/* GlobalBanner + page content */}
</GlobalHeader>
1.3 GlobalBanner
Files

`Banners/GlobalBanner.tsx`

`Banners/GlobalBanner.css`

These live inside `src/components/Banners/` to group banner-specific assets.

Role

The GlobalBanner is the Thinkorswim-style black banner that sits under the AppBar and above the main dashboard:

Shows connection status (“Connected / Disconnected”, last live tick time).

Provides account selection (dropdown) for active trading account.

Displays buying power / net liquidity metrics for the selected account.

Hosts top-level workspace tabs: Home / Trade / Futures / Global.

Optionally shows child tabs under each parent (e.g., “Activity & Positions”).

Key responsibilities

Polls the quotes API (e.g. /api/quotes/latest) to determine connection state and last update.

Fetches all accounts from /api/actandpos/accounts and exposes a dropdown:

Selected account drives:

Option Buying Power

Stock Buying Power

Net Liq

Derives the active parent tab from location.pathname.

Handles navigation for parent and child tabs using useNavigate.

Important behaviors

Connection state:

✅ Connected: green pill with live time (Realtime data · HH:MM:SS).

❌ Disconnected: red pill with “Waiting for live feed”.

Account dropdown:

Uses account list (e.g. broker_account_id + display_name) as options.

Selected account state can be shared with pages (e.g. Activity & Positions) to pass ?account_id= to backend endpoints.

Styling

.global-banner sets black background and stacked rows.

.home-connection, .home-connection-dot, .home-connection-details control connection pill appearance.

.home-account-select styles the green-on-black account <select> element.

.global-banner-balances, .home-balance-value show numeric BP/NetLiq values in the second row.

.global-banner-tabs, .home-nav-button implement the parent tab ribbon.

.global-banner-subtabs, .home-nav-button-child implement child tabs.

1.4 ProtectedRoute
File

ProtectedRoute.tsx

Role

ProtectedRoute is a route guard component for react-router-dom:

Wraps routes that should only be accessible by authenticated users.

Redirects unauthenticated users to a login/landing page.

Typically used in the app router when defining /app/* routes.

Key responsibilities

- Reads authentication state from the shared `useAuth()` hook. AuthContext (not localStorage) is the single source of truth, so routing stays in sync with the axios Authorization header.
- If `isAuthenticated` is false it redirects via `<Navigate>` to `/auth/login?next=…`.
- If the user is authenticated it renders the requested route element (usually inside `GlobalHeader` + `GlobalBanner`).

Logout is centralized: the drawer’s “Sign out” button calls `useAuth().logout()`, which clears both `thor_access_token` and `thor_refresh_token` keys and removes the default Authorization header. Do not manipulate tokens directly inside individual components.

Example usage

tsx
Copy code
<Route
  path="/app/*"
  element={
    <ProtectedRoute>
      <GlobalHeader>
        <GlobalBanner />
        {/* page content here */}
      </GlobalHeader>
    </ProtectedRoute>
  }
/>
2. Dashboard Grid Components
Dashboard grids are used to lay out modular tile apps (charts, tables, positions, news, etc.) in a fixed grid.

2.1 TwoByThreeGrid (2×3 = 6 tiles)
Files

Grid2x3/TwoByThreeGrid.tsx 
TwoByThreeGrid


Grid2x3/TwoByThreeGrid.css 
TwoByThreeGrid


Role

Static 2×3 dashboard grid:

2 columns, 3 rows, max 6 tiles.

Each tile has a header (title + slot label) and a scrollable body.

Used for layouts like the main Home or Global view.

API

ts
Copy code
export type DashboardTile = {
  id: string;
  title: string;
  slotLabel?: string;
  hint?: string;
  children?: React.ReactNode;
};

type TwoByThreeGridProps = {
  tiles: DashboardTile[];
};
tiles length can be ≤ 6; grid pads empty slots with blank tiles.

Key behaviors

Tiles are rendered in row-major order.

Each tile:

Header: .tbt-title (title), .tbt-slot (e.g., “Slot 1”).

Body: .tbt-body:

Scrolls vertically (overflow-y: auto).

No horizontal scroll (overflow-x: hidden).

Renders either children content, or a hint string.

Styling

.tbt-grid defines the grid layout and tile sizing. 
TwoByThreeGrid


.tbt-body is the main container apps must fit within:

Apps should follow the APP_GUIDELINES.md document for width/height behavior.

2.2 TwoByThreeGridSortable
File

Grid2x3/TwoByThreeGridSortable.tsx 
TwoByThreeGridSortable


Role

Drag-and-drop (sortable) variant of the 2×3 grid:

Uses @dnd-kit/core and @dnd-kit/sortable for drag handles.

Keeps the same 2×3 layout but allows users to reorder tiles.

API

ts
Copy code
type TwoByThreeGridSortableProps = {
  tiles: DashboardTile[];
  onReorder?: (next: DashboardTile[]) => void;
};
tiles: current ordered list of dashboard tiles.

onReorder: callback fired when user drops a tile; receives the updated DashboardTile[].

Key behaviors

Uses a drag handle button (⋮⋮) (.tbt-drag-handle) in the tile header.

Only non-empty tiles are sortable; empty tile placeholders exist but are not draggable.

Computes new tile order via arrayMove when drag ends and calls onReorder.

2.3 TwoByTwoGrid (2×2, second row taller)
Files

Grid2x2/TwoByTwoGrid.tsx 
TwoByTwoGrid


Grid2x2/TwoByTwoGrid.css 
TwoByTwoGrid


Role

Static 2×2 dashboard grid where row 2 is twice the height of row 1:

Ideal for layouts where the bottom row hosts bigger charts or dense tables.

Same tile concept as 2×3 grid but with 4 tiles instead of 6.

API

ts
Copy code
type TwoByTwoGridProps = {
  tiles: DashboardTile[];
};
Uses DashboardTile type imported from the 2×3 grid.

Key behaviors

Up to 4 tiles, padded with empty-* placeholders if fewer.

Each tile:

Header: .g22-header, .g22-title, .g22-slot.

Body: .g22-body, similar behavior to .tbt-body.

Styling

.g22-grid defines:

2 columns.

2 rows, where the second row uses minmax(0, 2fr) to be taller. 
TwoByTwoGrid


.g22-tile-* classes set slightly different background shades for each tile.

.g22-body handles scroll behavior and content alignment.

2.4 TwoByTwoGridSortable
File

Grid2x2/TwoByTwoGridSortable.tsx 
TwoByTwoGridSortable


Role

Sortable 2×2 grid variant:

Same layout as TwoByTwoGrid.

Allows tiles to be dragged and reordered via @dnd-kit.

API

ts
Copy code
type TwoByTwoGridSortableProps = {
  tiles: DashboardTile[];
  onReorder?: (next: DashboardTile[]) => void;
};
Key behaviors

Uses SortableTile with a drag handle (.g22-drag-handle).

Maintains a 4-slot layout with placeholders for empty tiles.

Calls onReorder when a non-empty tile has been moved.

3. Ribbons
3.1 FooterRibbon
Files

FooterRibbon.tsx 
FooterRibbon


FooterRibbon.css 
FooterRibbon


Role

The FooterRibbon is a scrolling ticker at the bottom of the app:

Shows live market data scrolled horizontally (symbols, price, % change).

Intended to mirror a professional trading platform’s tape/ribbon.

Key responsibilities

Fetches data from /api/quotes/ribbon on mount and every 2 seconds.

Displays:

Symbol (e.g. /ES, NQ, etc.).

Last price.

Percentage change (formatted with sign and 2 decimal places).

Color-coded change (green for positive, red for negative).

Data shape

ts
Copy code
interface RibbonSymbol {
  symbol: string;
  name: string;
  price: number | string | null;
  last: number | string | null;
  change: number | string | null;
  change_percent: number | string | null;
  signal: string | null;
}

interface RibbonData {
  symbols: RibbonSymbol[];
  count: number;
  last_updated: string;
}
Styling & animation

.footer-ribbon: fixed height bar across the bottom of the screen.

.footer-ribbon-track: scrolls left-to-right using footer-ribbon-scroll keyframes.

.ribbon-item, .ribbon-symbol, .ribbon-price, .ribbon-change define text layout.

.ribbon-change.positive and .ribbon-change.negative color the changes green/red.

4. App Layout Guidelines
File

APP_GUIDELINES.md 
APP_GUIDELINES


This is a must-read for anyone building apps to be embedded inside grid tiles.

Key rules

Width

App containers must use width: 100% and max-width: 100%.

Always use box-sizing: border-box.

Never set fixed widths (e.g. 800px) that could overflow a tile.

Height

Containers should use height: 100% and min-height: 0.

Vertical scroll should be handled within a dedicated content region.

Overflow

Horizontal: always overflow-x: hidden.

Vertical: use overflow-y: auto on the inner content area when needed.

Structure pattern

Typical structure:

tsx
Copy code
const YourTileApp: React.FC = () => {
  return (
    <div className="your-app-container">
      <header className="your-app-header">
        {/* Optional fixed header */}
      </header>
      <div className="your-app-content">
        {/* Scrollable content */}
      </div>
    </div>
  );
};
Where:

css
Copy code
.your-app-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 100%;
  height: 100%;
  min-height: 0;
  box-sizing: border-box;
  overflow: hidden;
}

.your-app-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}
Purpose

Ensures every embedded app:

Fits neatly inside TwoByThreeGrid / TwoByTwoGrid tiles.

Never causes horizontal scrollbars.

Plays nicely with .tbt-body / .g22-body scroll behavior.

5. Putting It All Together
A typical ThorTrading page looks like:

tsx
Copy code
<ProtectedRoute>
  <GlobalHeader>
    <GlobalBanner />

    {/* Main page body */}
    <TwoByThreeGrid
      tiles={[
        { id: 'positions', title: 'Positions', children: <PositionsApp /> },
        { id: 'orders', title: 'Orders', children: <OrdersApp /> },
        { id: 'news', title: 'News', children: <NewsApp /> },
        // ...
      ]}
    />

    <FooterRibbon />
  </GlobalHeader>
</ProtectedRoute>
GlobalHeader: fixed AppBar + shell.

GlobalBanner: connection + account + tabs.

TwoByXGrid: tile layout for apps.

FooterRibbon: live ticker at the bottom.

ProtectedRoute: ensures the whole thing is only visible to authenticated users.

This COMPONENTS.md should give you and future-you a quick mental model of how the Components folder is structured and how each piece fits into the ThorTrading “terminal” experience.