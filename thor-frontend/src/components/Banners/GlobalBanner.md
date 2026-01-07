# GlobalBanner Component

The **GlobalBanner** is the Thinkorswim-style banner that sits directly under the blue `GlobalHeader` AppBar. It is responsible for:

- Showing **connection status** to the quotes engine.
- Displaying and allowing selection of the **active trading account**.
- Showing **buying power / net liquidity** for the selected account.
- Rendering top-level **navigation tabs** (`Home`, `Trade`, `Futures`, `Global`) and optional child tabs.
- Providing quick links (email, Home, Messages, Support, Chat Rooms, Setup).
- Providing a **Start Brokerage Account** CTA (with a paper-account guard modal).

---

## Files

- **Orchestrator:** `GlobalBanner.tsx`
- **Subcomponents:**
  - `TopRow.tsx` – connection status, account dropdown, status pill, quick links, setup CTA + guard modal
  - `BalanceRow.tsx` – Option/Stock buying power + Net Liq
  - `TabsRow.tsx` – parent & child navigation tabs
- **Shared types:** `bannerTypes.ts`
- **Styles:** `GlobalBanner.css`

---

## Data Sources / API Endpoints

### 1) Connection Status (quotes engine heartbeat)

The banner pings the quotes API every **5 seconds** to decide whether to show **Connected** or **Disconnected**.

- **Endpoint:** `GET /api/futures/quotes/latest?consumer=futures_trading`
- **Connected logic:** response JSON contains `rows` array with length > 0
- **UI values:**
  - `connectionLabel`: `"Connected"` / `"Disconnected"`
  - `connectionDetails`:
    - Connected: `Realtime data · <clock> (last feed <lastUpdate>)`
    - Disconnected: `Waiting for live feed`

**Notes**
- The displayed clock uses `useGlobalTimer()`’s `now` value.
- `lastUpdate` is updated when live data is present.

---

### 2) Account Dropdown (banner account selector)

The banner loads all accounts for the dropdown on mount:

- **Endpoint:** `GET /actandpos/accounts`
- **State:**
  - `accounts: AccountSummary[]`
  - `selectedAccountId: number | null`
- **Default selection:**
  - If nothing selected yet, it selects the **first account** returned.

**Dropdown option label**
- Displays: `{broker_account_id} ({display_name})` if `display_name` exists.

---

## Behavior & UI Logic

### A) Status pill (Paper / Live / Needs setup)

Status is derived from the **selected account**:

- `isPaperAccount` is true when `selectedAccount.broker` lowercased equals `"paper"`.
- `isApproved` is true when `selectedAccount.ok_to_trade` is truthy.

**Label rules**
- No selected account: `No accounts available`
- Paper: `Mode: Paper`
- Non-paper but not approved: `Needs setup`
- Non-paper and approved: `Live: <display_name|broker|Brokerage>`

**Variant rules**
- `paper` → blue
- `live` → green
- `warning` (no account / needs setup) → yellow

---

### B) “Start Brokerage Account” button (CTA)

The button currently behaves like this:

- If **no account selected** OR the selected account is **Paper**:
  - Opens `BrokersAccountModal` (paper guard)
  - Modal “Go to setup” navigates to `/app/user/brokers`

- Otherwise (non-paper account selected):
  - Navigates to `/app/trade`

> Important: This means “Start Brokerage Account” is not strictly “go to setup” today; it’s acting like a context-aware action.

---

### C) “Setup Brokerage Account” quick link

The right-side quick link always navigates to:

- `/app/user/brokers`

This is the canonical “Broker Connections” / setup page entry point.

---

## Balances Row

Balances come from the selected account object:

- Option Buying Power: `selectedAccount.option_buying_power`
- Stock Buying Power: `selectedAccount.stock_buying_power`
- Net Liq: `selectedAccount.net_liq`

Formatting:
- Converts string-like values to number and formats with 2 decimals.
- Shows `—` when no value / no account selected.

---

## Tabs Row

Parent tabs (Row 3):
- Home → `/app/home`
- Trade → `/app/trade`
- Futures → `/app/futures`
- Global → `/app/global`

Child tabs (Row 4):
- `home`: Activity & Positions (`/app/activity`), Account Statement (`/app/account-statement`)
- `futures`: placeholders Option A/B/C
- `global`: placeholders Tab 1/2
- `trade`: none

Active state:
- Parent tab is derived from current route path prefix.
- Child tab active state is exact path match.

---

## Suggested Naming / UX Clean-up (Recommended)

To reduce confusion between “start” vs “manage”:

- Rename **Start Brokerage Account** → **Manage Broker Connections** (or **Broker Setup**)
- Make the CTA always navigate to `/app/user/brokers`
- Keep the status pill as the “live/paper/needs setup” indicator

If you still want a “smart button,” split it into two:
- **Broker Setup** → `/app/user/brokers`
- **Go Trade** → `/app/trade` (only if account is live & approved)

