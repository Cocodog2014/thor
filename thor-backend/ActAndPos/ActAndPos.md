ActAndPos – Accounts & Positions Service

ActAndPos is the backend service that powers the Activity & Positions screens in ThorTrading. It provides a brokerage-agnostic view of:

Trading accounts (live + paper)

Intraday orders and fills

Current positions and P/L

The React ActivityPositions page consumes these APIs and renders a Thinkorswim-style “Today’s Trade Activity” + Position Statement dashboard.

App Overview

Django app: ActAndPos (verbose name “Accounts and Positions”) 

apps

Exposed via DRF (Django REST Framework) serializers + function-based views

Integrated into the main app router under /actandpos/... (see project-level URLs)

Consumed by the React route /app/activity, wrapped by AppLayout and the global chrome.

Data Model
Account

Represents a single brokerage account (real Schwab or Paper Trading). 

accounts

Key fields:

broker: "SCHWAB" or "PAPER"

broker_account_id: unique broker-side identifier

display_name: human-friendly name (e.g., Rollover IRA, Paper Trading)

currency: default USD

net_liq, cash

stock_buying_power, option_buying_power, day_trading_buying_power

updated_at: auto-updated timestamp

Important property:

ok_to_trade: True only if both net_liq > 0 and day_trading_buying_power > 0. Used by the API to signal whether the account is in good standing for new trades. 

accounts

Order

Tracks all orders for today’s trade activity for an account. 

orders

Key concepts:

side: "BUY" / "SELL"

status: "WORKING", "FILLED", "CANCELED", "PARTIAL", "REJECTED"

order_type: "MKT", "LMT", "STP", "STP_LMT"

account: FK → Account (related_name="orders")

symbol, asset_type (e.g. EQ, FUT, OPT, FX)

quantity, limit_price, stop_price

time_placed, time_last_update, time_canceled, time_filled

Orders are later surfaced through the Activity API grouped by status.

Position

Represents the current position snapshot for an account. 

positions

Key fields:

account: FK → Account (related_name="positions")

symbol, description, asset_type

quantity, avg_price, mark_price

realized_pl_open, realized_pl_day

multiplier: contract multiplier (e.g. ES = 50, CL = 1000)

currency, updated_at

Important computed properties:

market_value = quantity * mark_price * multiplier

cost_basis = quantity * avg_price * multiplier

unrealized_pl = market_value - cost_basis

pl_percent = unrealized_pl / |cost_basis| * 100 (0 if cost_basis is 0) 

positions

Uniqueness:

unique_together = ("account", "symbol", "asset_type") — one row per symbol/asset type per account.

Trade

Represents individual fills that can feed account statements and P&L. 

trades

Key fields:

account: FK → Account (related_name="trades")

order: FK → Order (related_name="trades", nullable)

exec_id: broker execution identifier

symbol, side, quantity, price

commission, fees

exec_time: timestamp of fill

Serializers
AccountSummarySerializer

Slim projection of Account used across the API and frontend. 

serializers

Fields:

id, broker, broker_account_id, display_name, currency

net_liq, cash

stock_buying_power, option_buying_power, day_trading_buying_power

ok_to_trade (read-only)

PositionSerializer

Projection of Position for UI display. 

serializers

Includes:

Identity: id, symbol, description, asset_type

Pricing: quantity, avg_price, mark_price

P&L: market_value, unrealized_pl, pl_percent, realized_pl_open, realized_pl_day

currency

OrderSerializer

Projection of Order for the Activity screen. 

serializers

Fields:

id, symbol, asset_type, side, quantity

order_type, limit_price, stop_price

status, time_placed, time_last_update, time_filled, time_canceled

Views & API Endpoints

All endpoints live in ActAndPos.urls and are currently registered as: 

urls

/actandpos/positions
/actandpos/activity/today


(Actual prefix depends on project-level URL routing, typically /api/actandpos/....)

Shared helper – get_active_account

Utility that chooses which account to use. 

accounts

Logic:

If ?account_id=<pk> is present → get_object_or_404(Account, pk=account_id)

Otherwise, uses Account.objects.first()

Raises ValueError if no accounts exist (API returns 400 with message).

GET /actandpos/activity/today

View: activity_today_view in views/orders.py

Purpose:
Return a snapshot of today’s trade activity and current positions for the active account.

Query params:

account_id (optional) – primary key of Account; if omitted, defaults via get_active_account.

Logic:

Resolve account via get_active_account.

Filter Order by:

account=account

time_placed__date = today

Group orders into:

working – status="WORKING"

filled – status="FILLED"

canceled – status="CANCELED"

Fetch current Position rows for the same account.

Return:

{
  "account": { ...AccountSummarySerializer },
  "working_orders": [ ...OrderSerializer ],
  "filled_orders": [ ...OrderSerializer ],
  "canceled_orders": [ ...OrderSerializer ],
  "positions": [ ...PositionSerializer ],
  "account_status": {
    "ok_to_trade": true,
    "net_liq": "105472.85",
    "day_trading_buying_power": "6471.41"
  }
}


account_status is currently a convenience wrapper that re-exposes key account fields plus ok_to_trade. 

orders

Frontend usage:

ActivityPositions.tsx hits /actandpos/activity/today every 15 seconds and renders:

Top banner: Account name, Net Liq, BP

Three order tables: Working / Filled / Canceled

Position Statement table

Account status footer (“OK TO TRADE” vs “REVIEW REQUIRED”).

GET /actandpos/positions

View: positions_view in views/positions.py 

positions

Purpose:
Return current positions plus account summary for the active account.

Query params:

account_id (optional) – same as above.

Response:

{
  "account": { ...AccountSummarySerializer },
  "positions": [ ...PositionSerializer ]
}


This endpoint is available for future UI (e.g., dedicated Positions page, mobile view, or other consumer services).

Django Admin

Admin is fully wired for manual inspection and debugging. 

admin

AccountAdmin:

Shows broker, account ID, currency, net liq, cash, buying powers, ok_to_trade, updated_at.

Inline positions and orders for that account.

PositionAdmin:

Shows quantities, prices, P/L, and updated timestamps.

Read-only computed fields: market_value, unrealized_pl, pl_percent.

OrderAdmin:

Filters by status, side, order type, asset type, account.

Date hierarchy on time_placed for intraday history.

TradeAdmin:

Shows fills with commission, fees, exec_time.

Searchable by symbol, account, exec_id, and order__broker_order_id.

Frontend Integration

The main app router exposes /app/activity which renders ActivityPositions. 

App

ActivityPositions is a polling client of /actandpos/activity/today, refreshing every 15 seconds to keep the dashboard live without WebSockets.

The rest of the ThorTrading UI (Home, Futures, etc.) is wrapped by AppLayout, which provides the global banner where an account selector and paper-trading toggle can be mounted later.

Future Extensions (Paper Trading & Account Selector)

Not implemented yet, but this is where the app will grow:

Account selector / dropdown in Global banner, listing real + paper accounts using Account rows.

Passing account_id from the selected account into:

/actandpos/activity/today?account_id=...

/actandpos/positions?account_id=...

A paper trading engine that:

Creates Order + Trade records in response to simulated orders.

Updates Position rows and Account buying power & P/L as fills occur.

This markdown file describes the baseline structure that paper trading will plug into.