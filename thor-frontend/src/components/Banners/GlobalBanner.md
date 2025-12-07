Here’s a markdown doc you can drop in as GlobalBanner.md (or components/GlobalBanner.md).

# GlobalBanner Component

The **GlobalBanner** is the black, Thinkorswim-style banner that sits directly under the blue `GlobalHeader` AppBar. It is responsible for:

- Showing **connection status** to the quotes engine.
- Displaying and allowing selection of the **active trading account**.
- Showing **buying power / net liquidity** for the selected account.
- Rendering top-level **navigation tabs** (`Home`, `Trade`, `Futures`, `Global`) and optional child tabs.
- Providing quick links (email, Messages, Support, Chat Rooms, Setup). :contentReference[oaicite:0]{index=0}  

---

## Files

- **Component:** `GlobalBanner.tsx` :contentReference[oaicite:1]{index=1}  
- **Styles:** `GlobalBanner.css` :contentReference[oaicite:2]{index=2}  

---

## Responsibilities & Behavior

### 1. Connection Status

- Uses a polling effect to hit the quotes endpoint:

  ```ts
  const response = await fetch(
    '/api/quotes/latest?consumer=futures_trading',
    { cache: 'no-store' },
  );


Expects a JSON response shaped like:

{ rows?: unknown[] }


Logic:

const rows = Array.isArray(data?.rows) ? data.rows : [];
const hasLiveData = rows.length > 0;

if (hasLiveData) {
  setConnectionStatus('connected');
  setLastUpdate(new Date().toLocaleTimeString());
} else {
  setConnectionStatus('disconnected');
}


The effect runs once on mount and re-checks every 5 seconds using setInterval. Cleanup cancels the interval and prevents state updates after unmount. 

GlobalBanner

Rendered text:

connectionLabel ⇒ "Connected" or "Disconnected".

connectionDetails:

Connected + lastUpdate → Realtime data · HH:MM:SS

Connected without lastUpdate → Realtime data

Disconnected → Waiting for live feed

Visual representation:

.home-connection wrapper plus .home-connection-dot.

Green (emerald) styles for connected, red styles for disconnected. 

GlobalBanner

2. Accounts & Account Selector

Loads all accounts from:

api.get<AccountSummary[]>('/actandpos/accounts', {
  headers: { 'Cache-Control': 'no-store' },
});


AccountSummary interface: 

GlobalBanner

interface AccountSummary {
  id: number;
  broker: string;
  broker_account_id: string;
  display_name: string;
  currency: string;
  net_liq: string;
  cash: string;
  stock_buying_power: string;
  option_buying_power: string;
  day_trading_buying_power: string;
  ok_to_trade: boolean;
}


On successful load:

Stores the list in accounts state.

If nothing is selected yet, defaults selectedAccountId to the first account’s id.

Selected account is computed as:

const selectedAccount =
  (selectedAccountId !== null
    ? accounts.find((a) => a.id === selectedAccountId)
    : accounts[0]) || null;


The dropdown:

{accounts.length > 0 ? (
  <select
    className="home-account-select"
    aria-label="Select trading account"
    value={selectedAccount ? selectedAccount.id : ''}
    onChange={(e) => setSelectedAccountId(Number(e.target.value))}
  >
    {accounts.map((acct) => (
      <option key={acct.id} value={acct.id}>
        {acct.broker_account_id}
        {acct.display_name ? ` (${acct.display_name})` : ''}
      </option>
    ))}
  </select>
) : (
  <span className="home-account-id">No accounts</span>
)}


If the request fails, it logs an error and falls back to No accounts. 

GlobalBanner

3. Balances Row

The second row shows three balance values for the currently selected account:

Option Buying Power

Stock Buying Power

Net Liq

Each value:

Uses formatCurrency helper:

const formatCurrency = (value?: string | null) => {
  if (value === null || value === undefined) return '—';
  const num = Number(value);
  if (Number.isNaN(num)) return value ?? '—';
  return num.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};


Renders like:

{selectedAccount
  ? `$${formatCurrency(selectedAccount.option_buying_power)}`
  : '—'}


Styling:

The row uses .global-banner-balances.home-balances. 

GlobalBanner

.home-balance-value styles the numeric value (bold, light text).

4. Navigation Tabs
Parent Tabs

Configured in parentTabs:

const parentTabs = [
  { label: 'Home',    path: '/app/home',    key: 'home' },
  { label: 'Trade',   path: '/app/trade',   key: 'trade' },
  { label: 'Futures', path: '/app/futures', key: 'futures' },
  { label: 'Global',  path: '/app/global',  key: 'global' },
];


deriveParentKey() picks which tab to highlight based on location.pathname. 

GlobalBanner

Clicks:

const handleParentClick = (tabKey: string, tabPath: string) => {
  ignorePathSyncRef.current = true;
  setActiveParentKey(tabKey);
  navigate(tabPath);
};


Rendered as .home-nav container with .home-nav-button buttons. Active tab gets .active styling (amber border + darker background). 

GlobalBanner

Child Tabs (Subtabs)

Defined in childTabsByParent, keyed by parent key:

home → “Activity & Positions”, “View 2”, “View 3”

futures → “Option A / B / C”

global → “Tab 1 / Tab 2”

trade → (empty array). 

GlobalBanner

Subtabs row renders only if childTabs.length > 0.

Clicking a child tab:

const handleChildClick = (parentKey: string, path: string) => {
  ignorePathSyncRef.current = true;
  setActiveParentKey(parentKey);
  navigate(path);
};


Styled by .global-banner-subtabs container and .home-nav-button-child buttons. Active child has green border (#10b981) and lighter text. 

GlobalBanner

Layout & Styling Details

Top-level container:

.global-banner {
  width: 100%;
  display: flex;
  flex-direction: column;
  background-color: #0a0a0a;
  border-bottom: 1px solid #262626;
  padding: 0.25rem 0.75rem 0;
  gap: 0.2rem;
  font-size: 0.675rem;
  box-sizing: border-box;
}


Row 1 (.global-banner-row-top):

display: grid; grid-template-columns: auto 1fr;

Left side: .global-banner-left — connection + account selector.

Right side: .global-banner-right — email + quick links.

Row 2: .home-balances — flex layout with wrapping support.

Row 3: .home-nav — parent tabs.

Row 4: .global-banner-subtabs — child tabs.

Quick links:

.home-contact-link, .home-quick-link render as inline-flex, no borders, and highlight to amber on hover. 

GlobalBanner

Accessibility Notes

The account dropdown has aria-label="Select trading account" to satisfy accessibility/linting requirements. 

GlobalBanner

The top-level banner wrapper uses:

<div
  className="global-banner"
  role="navigation"
  aria-label="Primary navigation banner"
>


to identify the region as navigational content for assistive technologies.

How to Modify / Extend

Change which endpoint drives connection status

Update the fetch('/api/quotes/latest?consumer=futures_trading') URL if your backend path or consumer name changes.

Add more parent or child tabs

Add to the parentTabs array.

Add corresponding entries to childTabsByParent if needed.

Customize which balances show

Modify the three <span> blocks in the balances row and/or extend AccountSummary if additional numeric fields are needed.

Change account sort order or filtering

Adjust the /actandpos/accounts backend view (sorting/filtering) or process accountList before storing it in state.

Summary

GlobalBanner is the live status + navigation rail for Thor’s War Room:

It reflects real-time health of the quotes engine.

It controls which trading account is “active” at the UI level.

It summarizes core account balances.

It provides quick navigation between major workspaces and their sub-views.

Any layout or behavior changes that affect the top-of-screen trading strip should go through this component and its CSS.