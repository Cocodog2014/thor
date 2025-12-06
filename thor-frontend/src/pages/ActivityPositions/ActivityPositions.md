Activity & Positions – Frontend Documentation

File: src/pages/ActivityPositions/ActivityPositions.tsx
Purpose: Provide a single unified view showing the account’s intraday trading activity, working/filled/canceled orders, open positions, and account trading status.

This screen is the frontend counterpart to the backend endpoint:

GET /actandpos/activity/today


It refreshes automatically every 15 seconds, giving the user a near-real-time dashboard of their trading day.

Overview

The Activity & Positions page is composed of four major sections:

Header – Today’s Trade Activity & Account Summary

Orders Sections – Working, Filled, and Canceled Orders

Position Statement – Open positions with P/L metrics

Account Status Footer – Tradeability indicator

This page is read-only.
All actual trading (paper orders, fills, cancels) is handled in the Trades app.
This component simply displays the current snapshot from the backend.

Data Flow
Backend Endpoint

The page calls:

api.get<ActivityTodayResponse>("/actandpos/activity/today")


Backend response (ActivityTodayResponse) contains:

account → summary of the active trading account

working_orders → list of intraday orders with status="WORKING"

filled_orders → orders the paper engine filled

canceled_orders → orders manually canceled or system-canceled

positions → list of open positions for the account

account_status.ok_to_trade → boolean flag

The request repeats every 15 seconds, controlled by a setInterval inside useEffect.

Component Structure

The component is divided into small functional helpers and one main component.

1. OrdersSection Component

Purpose: Render a titled table of orders for a given status.
Props:

{ title: string; orders: Order[] }


Displays:

Time

Side

Qty

Symbol

Type

Limit

Stop

Status

If no orders exist, shows "No records."

💡 This is used 3 times:

<OrdersSection title="Working Orders" orders={data.working_orders} />
<OrdersSection title="Filled Orders" orders={data.filled_orders} />
<OrdersSection title="Canceled Orders" orders={data.canceled_orders} />

2. PositionsStatement Component

Purpose: Display all open positions and their P/L metrics.
Props:

{ positions: Position[] }


Columns:

Instrument (symbol)

Qty

Trade Price (avg_price)

Mark (current mark price)

Net Liq (market_value)

% Change (pl_percent)

P/L Open (realized or unrealized depending on account model)

P/L Day

If no positions exist, shows "No open positions."

This is aligned with TOS/IBKR layout philosophy.

3. Main Component – ActivityPositions
const ActivityPositions: React.FC = () => { ... }

Internal State
const [data, setData] = useState<ActivityTodayResponse | null>(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);

useEffect – data loading & auto-refresh

Calls the API on mount

Sets a 15-second interval to refresh automatically

Cancels requests safely using a cancelled flag

This ensures the UI stays synchronized with:

new paper orders

fills created by the paper engine

updated positions

updated account net liq & buying power

Loading & Error Handling

Before data arrives:

Loading activity and positions…


On error:

Failed to load activity and positions.

4. Header Row: Today’s Trade Activity
<h2>Today's Trade Activity</h2>


Displays:

Account name (display_name or broker_account_id)

Net Liq

Buying Power (day_trading_buying_power)

This header is the future place where the order ticket can appear (design choice; currently the trade ticket lives in /app/trade).

5. Orders Sections

Three instance of OrdersSection:

<OrdersSection title="Working Orders" orders={data.working_orders} />
<OrdersSection title="Filled Orders"  orders={data.filled_orders} />
<OrdersSection title="Canceled Orders" orders={data.canceled_orders} />


These tables populate directly from the account’s intraday orders created by:

The paper trading engine

Future real broker sync

6. Position Statement

This displays the account’s open positions and their live profit metrics.

It uses:

<PositionsStatement positions={data.positions} />


Values come from backend model properties:

market_value

pl_percent

realized_pl_open

realized_pl_day

These are automatically updated whenever:

a trade is executed

mark price changes (future integration)

positions update due to orders

7. Account Status Footer

At the bottom:

ACCOUNT STATUS: OK TO TRADE


or

ACCOUNT STATUS: REVIEW REQUIRED


This uses the backend logic that determines:

missing info

insufficient balances

regulatory flags

or (in future) pattern day trader checks

Styling uses:

ap-status-ok

ap-status-warning

Automatic Refresh Logic

The component’s refresh system ensures a near real-time display:

useEffect(() => {
  load();
  const interval = setInterval(load, 15000);
  return () => clearInterval(interval);
}, []);


This ensures:

Orders update without manual refresh

Filled orders appear within 15 seconds

Positions update immediately after fills

Net Liq and BP remain current

Later we can upgrade this to WebSockets for instant updates.

Integration With Trades App

Even though Activity & Positions is read-only, it relies on trading events:

Paper trades from Trades/paper_order_view

Trade rows created in Trades/models.py

Account/Position updates from place_paper_order

The page does not place trades.
It only displays trading results.

This perfectly fits the architecture:

App	Responsibility
Trades	Execute trades, create orders, create fills
ActAndPos	Display account state, positions, intraday activity
Styling Reference

Styles come from:

src/pages/ActivityPositions/ActivityPositions.css


Includes classes:

.ap-screen

.ap-body

.ap-title-row

.ap-section

.ap-table

.ap-status-row

etc.

These unify the screen with the rest of the ThorTrading UI.

Summary

ActivityPositions.tsx is the intraday trading dashboard for the active account. It gives the user:

full visibility into daily orders (working/filled/canceled)

full position details with P/L metrics

up-to-date account health (Net Liq, BP, OK to trade)

automatic background refresh of all data

This page works hand-in-hand with:

Trades → paper trading engine

ActAndPos → activity snapshot serializer

It is the "What happened today?" page for your trading platform.