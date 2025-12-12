DevelopmentFrontend.md
Thor Trading — Frontend Development Guide (Updated)

Last updated: After Global Theme + CSS overhaul (past 2 days).

1. Overview

The Thor frontend uses a unified layout, a central global theme, and consistent component-level styling. All screens must follow the same structural and color rules defined in global.css.

The frontend structure:

---------------------------------------------------------
| GLOBAL HEADER (static)                                |
---------------------------------------------------------
| GLOBAL BANNER (connection, account, tabs)             |
---------------------------------------------------------
| MAIN CONTENT SCROLL AREA                              |
|   (page-specific UI: grids, tables, cards, forms)     |
---------------------------------------------------------
| FOOTER RIBBON (scrolling futures ticker)              |
---------------------------------------------------------


Key principles:

The header, banner, and footer ribbon never scroll.

Only the page content scrolls.

All colors and shadows come from the global theme.

2. Global CSS Theme System (global.css)

The global theme now powers every component.

Background layers
--bg-0: #000000;   /* Global canvas */
--bg-1: #020617;   /* Cards / panels */
--bg-2: #030712;   /* Section headers */
--bg-3: #111827;   /* Hover / dark panels */

Text colors
--text-strong:  #f3f4f6;
--text-normal:  #e5e7eb;
--text-muted:   #9ca3af;
--text-subtle:  #6b7280;

Accents & status
--accent-yellow:       #facc15;
--accent-yellow-soft:  #fbbf24;

--green: #4ade80;
--red:   #f97373;

--blue:      #1e88e5;
--blue-soft: #64b5f6;

Borders, shadows, input styling
--border-1:  #1f2937;
--border-2:  #374151;

--shadow-soft:   0 8px 32px rgba(0,0,0,0.4);
--shadow-strong: 0 18px 45px rgba(0,0,0,0.6);

--input-bg:          #020617;
--input-border:      #30363d;
--input-focus-border:#58a6ff;

Rules

✔ No component should define its own colors.
✔ All colors come from theme variables.
✔ All cards/tables follow:

Background = --bg-1

Header = --bg-2

Hover = --bg-3
✔ NEVER use hex colors inside component CSS.

3. Global Layout Rules
html, body, #root

Height: 100%

Background: --bg-0

No scrolling here

app-content-scroll

The only scrollable region.

.app-content-scroll {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
}


Everything else must remain fixed.

4. Updated Components (past 2 days)

Below are all components that were updated and standardized.

4.1 Global Banner (Updated)

Behavior preserved, visuals unified.

Changes:

Background now uses var(--bg-1) (deep navy) to match header.

Connection indicator uses theme greens/reds.

Tab and subtabs re-themed (accent yellow + green).

Borders + text updated to theme variables.

Banner + Header now appear as a single unified top bar.

4.2 Collapsible Drawer (Updated)

Changes:

Background uses var(--thor-sidebar-gradient) + theme text.

All borders → theme borders.

Selected nav item uses theme blue.

Hover state matches global hover patterns.

Drawer labels fade out properly when collapsed.

No hard-coded colors remain.

This drawer is now visually consistent with the rest of the app.

4.3 Account Statements (FULL Rewrite + Theme Migration)

This was the biggest update.

What was fixed:

Old layout restored (collapsibles, header bars, correct spacing).

All colors converted to theme variables.

Inputs, buttons, and radio selectors use global input styles.

Section headers use --bg-2.

Hover rows use --bg-3.

Borders + labels use --border-1 and --text-muted.

Collapsible icons restored.

No double-scrolling issues.

This page is now visually aligned with Activity & Positions and Market pages.

4.4 Activity & Positions (Updated)

Adopted same theme rules as Account Statements.

Status colors → theme green/red.

Inputs → theme input styling.

Hover rows → --bg-3.

Page-level padding and layout unified.

4.5 Market Sessions (Futures Open Session)

All card backgrounds mapped to theme.

Delta colors use theme green/red.

Triangle indicators themed.

Table rows themed.

Cards now share consistent spacing and borders.

4.6 Futures Home (Updated)

Background gradient updated (--bg-1 → --bg-0 fade).

Unified padding, spacing, and scroll rules.

4.7 Futures RTD Cards / Total Composite Card

Total card re-themed, keeping orange identity.

Background/border/shadows updated.

Typography uses global variables.

Composite values and pill indicators aligned with theme.

5. Grid Systems

Two shared grid systems were fully converted to global theme colors.

5.1 TwoByThreeGrid (2×3)
Updated rules:

Tile backgrounds:

Top row → --bg-1

Lower row → --bg-2

Border → --border-1

Shadow → --shadow-soft

Drag handle → --text-muted

Tile titles → --text-strong

Body text → --text-normal

5.2 TwoByTwoGrid (2×2)

Same updates as 2×3:

Tile backgrounds themed

Titles/subtitles updated

Drag handle themed

No residual hex colors

Both grid systems now share identical styling logic.

6. Footer Ribbon (Updated)

Theme yellow for symbols

Theme green/red for deltas

Background uses --bg-0

Smooth infinite scroll preserved

Ribbon now matches new global theme without contrast issues.

7. CSS Development Standards
1. Never hard-code colors.

Use global theme variables.

2. Page CSS must NEVER modify global layout.

Pages cannot touch:

Header

Banner

Drawer

Footer Ribbon

html/body

3. Scroll only inside .app-content-scroll

No component should create unintended scrollbars.

4. Use theme background hierarchy

Panels → --bg-1

Section headers → --bg-2

Hover/selected → --bg-3

5. Borders + shadows are standardized

Border: --border-1

Shadow: --shadow-soft

6. Consistent typography

Titles → --text-strong

Labels → --text-muted

Body → --text-normal

7. Inputs & Buttons follow theme

input, select, textarea, button use global input settings.

8. Directory Overview

The frontend lives under `src/` and is organized as follows:

Src/
 ├─ assets/
 ├─ components/
 │   ├─ Banners/
 │   │   └─ GlobalBanner.css / GlobalBanner.tsx (if present)
 │   ├─ CommanderWelcome/
 │   ├─ Drawer/
 │   │   └─ CollapsibleDrawer.css / CollapsibleDrawer.tsx
 │   ├─ Grid2x2/
 │   │   └─ TwoByTwoGrid.css / TwoByTwoGrid.tsx
 │   ├─ Grid2x3/
 │   │   └─ TwoByThreeGrid.css / TwoByThreeGrid.tsx
 │   ├─ Header/
 │   │   └─ GlobalHeader.css / GlobalHeader.tsx
 │   ├─ Ribbons/
 │   │   └─ FooterRibbon.css / FooterRibbon.tsx
 │   ├─ Components.md          ← component notes / docs
 │   └─ ProtectedRoute.tsx
 │
 ├─ context/
 │   ├─ AuthContext.tsx
 │   ├─ GlobalTimerContext.tsx
 │   └─ TradingModeContext.tsx
 │
 ├─ hooks/
 │   ├─ DragAndDrop.ts
 │   └─ useThorData.ts
 │
 ├─ layouts/
 │   ├─ AppLayout.tsx          ← wraps header, banner, content, ribbon
 │   └─ AuthLayout.tsx
 │
 ├─ pages/
 │   ├─ AccountStatement/
 │   ├─ ActivityPositions/
 │   ├─ Futures/
 │   ├─ FxReport/
 │   ├─ GlobalMarkets/
 │   ├─ Home/
 │   ├─ Trade/
 │   └─ User/
 │
 ├─ services/
 │
 ├─ styles/
 │   └─ global.css             ← global theme + base layout
 │
 ├─ types/
 │
 ├─ App.tsx
 ├─ main.tsx
 └─ theme.ts

9. Summary

The frontend is now:

✔ Fully theme-driven
✔ Consistent across all screens
✔ Correctly structured with a single scroll area
✔ Visually unified (header → banner → content → ribbon)
✔ Easy to update or reskin globally
✔ Free of old hex-coded greys/blacks
✔ With restored functionality (collapsibles, hover states, tabs)

10. Auth & Token Lifecycle (Dec 2025)

Recent fixes (Dev-1 branch) harden authentication between the React app and the Django API:

• Storage keys are centralized in src/constants/storageKeys.ts: AUTH_ACCESS_TOKEN_KEY = thor_access_token and AUTH_REFRESH_TOKEN_KEY = thor_refresh_token. No other keys should be used for JWTs.
• AuthContext.tsx owns token state. Login now calls login(accessToken, refreshToken?) which persists both keys and immediately updates axios defaults via setAuthHeader(). Logout clears both keys and removes the Authorization header.
• ProtectedRoute reads useAuth().isAuthenticated instead of hitting localStorage directly, so React state is the source of truth and future storage changes won’t break routing guards.
• api.ts no longer re-injects Authorization from localStorage on every request. AuthContext is the only place that sets/clears api.defaults.headers.common.Authorization. The request interceptor’s role is now just to strip that header from public endpoints.
• The refresh interceptor still rotates access tokens via /users/token/refresh/ and forces a full logout (clearing both keys + redirecting to /auth/login) if refresh fails.

Acceptance tests for the auth flow:

1. Login as admin, call GET /api/users/profile/ — response must show admin@360edu.org. Logout. Check Application → Local Storage: thor_access_token and thor_refresh_token should be deleted. If not, fix logout.
2. Login as tom@gmail.com — thor_access_token must change, axios requests must authenticate as Tom (profile endpoint returns Tom).
3. Leave the frontend idle until the access token expires. The next API call should transparently refresh using thor_refresh_token; if refresh fails (expired/invalid), the app must redirect to /auth/login and both storage keys must be cleared.

These rules prevent “token drift” where the UI shows one user while API requests go out as another. Any future auth work (broker connections, multi-user dashboards, etc.) should continue to run through AuthContext so there is a single place managing JWTs.

If you'd like, I can now:

✅ Put this MD into Canvas as an editable document
or
✅ Add diagrams for layout & component flow


