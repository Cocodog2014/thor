Trades Frontend – Trade Workspace & Paper Ticket

The Trades frontend is the React “Trade Workspace” for ThorTrading. It sits under the main AppLayout, uses the global banner/nav, and talks to:

GET /actandpos/activity/today for the current account snapshot

POST /trades/paper/order for paper trades

The goal is to give you a clean Trade screen where you can submit paper orders and see them reflected in the existing Activity & Positions views.

1. Layout & Routing
App shell – AppLayout

AppLayout wraps all authenticated app pages (Home, Trade, Activity, etc.) with:

GlobalHeader (top AppBar)

GlobalBanner (blue strip with connection status + nav tabs)

Scrollable content area

FooterRibbon at the bottom 

AppLayout

const AppLayout: React.FC<AppLayoutProps> = ({ children, ...toggles }) => {
  return (
    <GlobalHeader {...toggles}>
      <GlobalBanner />
      <div className="app-content-scroll">
        {children}
      </div>
      <FooterRibbon />
    </GlobalHeader>
  );
};


The Trade workspace is rendered inside this app-content-scroll region when the route matches /app/trade.

In the router (App.tsx), you should have something like:

<Route path="/app" element={<AppLayout ...>}>
  <Route path="home" element={<Home />} />
  <Route path="trade" element={<Trades />} />
  <Route path="activity" element={<ActivityPositions />} />
</Route>

2. Trade Workspace Pages
2.1 TradeHome.tsx – simple placeholder

TradeHome is a minimal stub page that can be used as a landing view or parent wrapper if you later want multiple sub-tabs under Trade. 

TradeHome

const TradeHome: React.FC = () => (
  <div style={{ padding: '1rem' }}>
    <h1>Trade Workspace</h1>
    <p>Trade tools will appear here once configured.</p>
  </div>
);


Right now, the real functionality lives in Trades.tsx (below). You can either:

Route /app/trade → Trades, and ignore TradeHome, or

Route /app/trade → TradeHome and mount Trades as a child component later.

2.2 Trades.tsx – main Trade Workspace + Paper Ticket

File: src/pages/Trade/Trades.tsx 

Trades

This is the primary Trade screen. It:

Loads the current account via GET /actandpos/activity/today.

Renders a PaperOrderTicket for paper trades.

Lets you manually refresh account info after trades.

Key imports:

api – Axios instance pointing at your backend (/api/...).

toast – from react-hot-toast for success/error messages.

Types:

AccountSummary

ActivityTodayResponse

PaperOrderResponse
from ../../types/actandpos.

Data flow

On mount (and when refreshCounter changes), Trades calls:

const response = await api.get<ActivityTodayResponse>("/actandpos/activity/today");
setAccount(response.data.account);


If the request fails, it shows a friendly error message in the body.

Component structure
const Trades: React.FC = () => {
  const [account, setAccount] = useState<AccountSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshCounter, setRefreshCounter] = useState(0);

  useEffect(() => {
    // fetch account via /actandpos/activity/today
  }, [refreshCounter]);

  // loading + error states ...

  return (
    <div className="trade-screen">
      <header className="trade-header">
        <div>
          <h1>Trade Workspace</h1>
          <p>We are building out the full experience. For now, use the paper ticket to send test orders.</p>
        </div>
        <button
          type="button"
          className="trade-refresh"
          onClick={() => setRefreshCounter((prev) => prev + 1)}
        >
          Refresh Account
        </button>
      </header>

      <div className="trade-body">
        <PaperOrderTicket
          account={account}
          onOrderPlaced={() => setRefreshCounter((prev) => prev + 1)}
        />
      </div>
    </div>
  );
};


Refresh button increments refreshCounter, which re-runs the effect and re-fetches /actandpos/activity/today.

After each paper order, onOrderPlaced also increments refreshCounter, giving you a fresh snapshot of account state.

3. PaperOrderTicket Component

Defined inside Trades.tsx. 

Trades

Purpose

A compact order ticket that submits paper trades to:

api.post<PaperOrderResponse>("/trades/paper/order", payload);


matching the backend Trades app API (POST /api/trades/paper/order after routing).

Props
type PaperOrderTicketProps = {
  account: AccountSummary;
  onOrderPlaced: () => void;
};


account – active account (display name, broker account id, etc.).

onOrderPlaced – callback to let the parent refresh account/activity data.

Internal state

symbol – text input, uppercased on submit.

side – "BUY" or "SELL".

quantity – string; converted to number on submit.

orderType – "MKT" (market) or "LMT" (limit).

limitPrice – numeric string; required for limit orders.

submitting – boolean flag to disable the button while a request is in flight.

Validation logic

Before sending the API request, handleSubmit enforces:

Symbol is not empty.

Quantity > 0.

For LMT orders, limitPrice must be provided.

If invalid, it uses toast.error(...) to show a message and early-return.

Request body

On successful validation, it builds:

const payload = {
  symbol: sym,                 // uppercase symbol
  asset_type: "EQ",            // hard-coded for now
  side,                        // "BUY" | "SELL"
  quantity: qty,               // numeric
  order_type: orderType,       // "MKT" | "LMT"
  limit_price: orderType === "LMT" ? Number(limitPrice.trim()) : null,
  stop_price: null,
};


and posts to:

const response = await api.post<PaperOrderResponse>(
  "/trades/paper/order",
  payload
);

Response handling

Given a PaperOrderResponse:

interface PaperOrderResponse {
  account: AccountSummary;
  order: Order;
  position: Position | null;
}


…it does:

toast.success("Paper BUY 1 ES submitted.") (message includes side, quantity, symbol).

Clears symbol, resets quantity to "1", clears limitPrice.

Calls onOrderPlaced() so the parent (Trades) can refresh account data.

On error, it logs the error, extracts err.response.data.detail if available, and calls toast.error(...).

UI / Layout

The ticket is wrapped in:

<div className="trade-ticket">
  <div className="trade-ticket-title">
    Paper Trading – Quick Ticket ({account.display_name || account.broker_account_id})
  </div>
  <form className="trade-ticket-form" onSubmit={handleSubmit}>
    {/* Symbol, Side, Qty, Type, Limit, Submit */}
  </form>
</div>


Styling lives in Trades.css (same folder), which you can expand to match your ThorTrading look and feel.

4. Supporting Pieces
Home Dashboard – Home.tsx

Home isn’t directly part of Trades, but it participates in the overall app layout where the Trade tab lives in the global banner. The Home page renders a draggable 2×3 grid of dashboard tiles (Global Markets, RTD, News, etc.). 

Home

const Home: React.FC = () => {
  const { tiles, setTiles } = useDragAndDropTiles(BASE_TILES, { storageKey: STORAGE_KEY });

  return (
    <div className="home-screen">
      <main className="home-content">
        <TwoByThreeGridSortable tiles={tiles} onReorder={setTiles} />
      </main>
    </div>
  );
};


This is the “Home” tab next to “Trade” in the global nav.

AuthLayout

Used for login / auth flows, not trade-specific, but included here for completeness. 

AuthLayout

const AuthLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'flex-start', justifyContent: 'center' }}>
    <div style={{ width: '100%', maxWidth: 560, marginTop: 64, padding: 16 }}>
      {children}
    </div>
  </div>
);

Environment switching – scripts/switch-env.mjs

Not Trade-specific, but important for making sure the frontend points at the correct backend (dev vs docker). 

switch-env

Usage (via npm script):

node scripts/switch-env.mjs dev
# or
node scripts/switch-env.mjs docker


This copies .env.<envName> → .env.local, which Vite uses for VITE_API_BASE_URL, ensuring calls like /actandpos/activity/today and /trades/paper/order hit the right backend instance.

5. How it all feels from the user’s perspective

User logs in and sees the Home dashboard under AppLayout.

In the blue banner nav, they click Trade → router navigates to /app/trade.

/app/trade renders <Trades /> inside AppLayout, so:

Top: GlobalHeader + GlobalBanner (connection status, account label, tabs).

Middle: Trade Workspace header + Paper Trading – Quick Ticket.

They enter:

Symbol: ES

Side: BUY

Qty: 1

Type: MKT

Hit Send Paper Order:

Frontend POSTs to /trades/paper/order.

Backend Trades app runs the paper engine, updates ActAndPos account/positions, returns order + account + position.

UI shows a toast and refreshes account via /actandpos/activity/today.

If they navigate to the Activity & Positions page (/app/activity), they see:

The same account with updated orders / positions / P&L, because it’s reading the same underlying data.