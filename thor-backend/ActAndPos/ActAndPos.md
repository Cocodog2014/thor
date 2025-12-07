ActAndPos – Accounts & Positions Service (Updated)

ThorTrading Core: Accounts, Orders (intraday), Positions, P&L Snapshot

ActAndPos is the backend service powering the Activity & Positions screen in ThorTrading.
It provides a brokerage-agnostic, real-time snapshot of:

Trading accounts (real + paper)

Intraday orders

Current positions

Current P&L computations

It intentionally does not contain historical fills or trade execution logic—those now live in the Trades app. ActAndPos focuses entirely on “What do I have right now?”

App Overview

Django App: ActAndPos (“Accounts and Positions”)

Exposed via DRF serializers + simple function-based views

Mounted under /actandpos/... in the project router (typically /api/actandpos/...)

Consumed by the React route: /app/activity, displayed inside the global layout

ActAndPos is the “live positions & account state” layer.
The Trades app references ActAndPos models when filling orders and updating positions.

Data Model
Account

Represents a user’s brokerage account (real Schwab or Paper).

Key fields:

broker – "SCHWAB" or "PAPER"

broker_account_id – unique identifier

display_name – e.g., Rollover IRA, Paper Account

currency – default USD

net_liq, cash

stock_buying_power, option_buying_power, day_trading_buying_power

updated_at

Important property:

ok_to_trade – calculated:
net_liq > 0 and day_trading_buying_power > 0

Used by both the Activity screen and the paper trading engine (Trades app) to indicate whether trading is permitted.

Order

Intraday order record for an account.
These are today’s orders only — fills (Trade objects) are stored in the Trades app now.

Key fields:

account – FK → Account (related_name="orders")

symbol, asset_type (EQ, FUT, OPT, FX)

side – "BUY" / "SELL"

status – "WORKING", "FILLED", "CANCELED", "PARTIAL", "REJECTED"

order_type – "MKT", "LMT", "STP", "STP_LMT"

quantity, limit_price, stop_price

time_placed, time_last_update, time_canceled, time_filled

Orders are grouped by status in the /activity/today API.

Position

Represents the current holdings snapshot for an account.

Key fields:

account – FK → Account (related_name="positions")

symbol, description, asset_type

quantity, avg_price, mark_price

realized_pl_open, realized_pl_day

multiplier (e.g., ES=50, CL=1000, equities=1)

currency, updated_at

Calculated fields:

market_value = qty × mark × multiplier

cost_basis = qty × avg_price × multiplier

unrealized_pl = market_value – cost_basis

pl_percent = unrealized_pl ÷ |cost_basis| × 100

Uniqueness:

(account, symbol, asset_type) ensures one row per unique position.

The Trades app updates these Position rows when fills occur.

Serializers
AccountSummarySerializer

Lightweight serializer used throughout ThorTrading (including the Trades app).
Fields include:

Identity + broker metadata

net_liq, cash

all buying power fields

ok_to_trade

PositionSerializer

Projects a Position into UI-ready values:

symbol, description, asset_type

qty, avg_price, mark_price

market_value, unrealized_pl, pl_percent

realized_pl_open, realized_pl_day

currency

OrderSerializer

Used by the Activity screen.

Includes all relevant intraday order details:
id, symbol, side, qty, order_type, limit/stop, status, timestamps.

Views & API Endpoints

Registered in ActAndPos.urls:

/actandpos/activity/today
/actandpos/positions


(Project-level routes usually prefix these with /api.)

Account Selection: get_active_account

Shared helper used across endpoints (and also by Trades during paper executions).

Logic:

If ?account_id=<id> is passed → load that account

Else → use Account.objects.first()

If none exist → return HTTP 400 with an error

GET /actandpos/activity/today

Primary API powering the ActivityPositions React page.

View: activity_today_view

Purpose

Return today’s orders + current positions + account status for the active account.

Logic

Fetch account via get_active_account

Filter today’s orders by time_placed__date = today

Group into:

working_orders

filled_orders

canceled_orders

Fetch current positions

Compute account_status (net_liq, BP, ok_to_trade)

Response
{
  "account": {...},
  "working_orders": [...],
  "filled_orders": [...],
  "canceled_orders": [...],
  "positions": [...],
  "account_status": {
    "ok_to_trade": true,
    "net_liq": "105472.85",
    "day_trading_buying_power": "6471.41"
  }
}

Frontend Usage

The React page polls this endpoint every 15 seconds to keep the dashboard live.

GET /actandpos/positions

View: positions_view

Purpose:
Return current positions + account summary without the orders.

Useful for standalone Positions pages or analytics.

Django Admin

Admin is fully wired for inspection and debugging:

AccountAdmin

broker, broker_account_id

buying powers, net_liq, cash

ok_to_trade

inlines: positions + orders

PositionAdmin

qty, avg_price, mark_price

market_value, unrealized_pl, pl_percent

read-only computed fields

OrderAdmin

status, side, order_type

filters for quick intraday triage

date hierarchy on time_placed

Note: TradeAdmin now lives in the Trades app, since fills were moved there.

Frontend Integration

Route: /app/activity
Component: ActivityPositions.tsx

Polls /actandpos/activity/today

Renders:

Account banner

Working / Filled / Canceled orders

Position statement

Account status indicator

This page is wrapped in the global app layout, which will later host the account selector and (optionally) a paper/live switch.

Relationship to the Trades App (Brief Reference)

While ActAndPos owns Accounts, Orders, Positions,
the Trades app owns:

Trade execution (paper engine)

Fills (Trade records)

Paper order APIs

Account Statement endpoints

Trades depends on ActAndPos to update Accounts and Positions during fills.

ActAndPos itself remains clean and focused:

Live account snapshot + intraday orders + positions.
No trade history, no execution engine inside this app.

Future Extensions Inside ActAndPos

Global account selector (frontend) wired into these endpoints

Optional cached snapshot service for mobile/performance

Additional projections: sector exposure, position sizing, risk metrics

(Trade history, reporting, and statements will continue to live exclusively in the Trades app.)