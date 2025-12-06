Trades – Orders, Fills & Paper Trading Engine

The Trades app owns everything related to executions and trading behavior:

Individual fills (Trade model)

The paper trading engine (simulated fills, P&L, buying power updates)

Paper order APIs used by the React “Trade” workspace

Django admin for reviewing fills

It depends on ActAndPos for accounts, orders, and positions, but keeps all trading logic isolated from the “Accounts & Positions” app.

App Overview

Django app config: TradesConfig (Trades/apps.py) 

apps

Database:

Trade rows live in the ActAndPos_trade table for backward compatibility. 

trade

Integrations:

FK to ActAndPos.Account

FK to ActAndPos.Order

Uses ActAndPos.Position and account fields when updating balances/positions. 

paper_engine

In short: ActAndPos answers “what do I have?”, and Trades answers “what did I do?” and “do a trade now”.

Data Model
Trade model

File: Trades/models.py 

trade

Represents an individual execution (fill), whether from live broker sync or paper trading.

Key fields:

account – FK → ActAndPos.Account (the account the fill belongs to)

order – FK → ActAndPos.Order (related_name="trades")

symbol – instrument symbol (e.g. ES, AAPL)

side – BUY / SELL (uses Order.SIDE_CHOICES from ActAndPos)

quantity – filled quantity

price – execution price

commission – commission charged

fees – exchange/other fees

exec_time – timestamp of the execution

exec_id – broker/exchange execution ID

Meta:

ordering = ("-exec_time",) – newest fills first

db_table = "ActAndPos_trade" – reuses the legacy table, so no data is lost when splitting the app.

String representation:

YYYY-MM-DD HH:MM:SS SIDE QTY SYMBOL


This keeps trade history centralized and usable for statements, reports, and analytics.

Serializers

File: Trades/serializers.py 

serializers

TradeSerializer

Simple DRF serializer for exposing fills in APIs:

Fields:

id

symbol

side

quantity

price

commission

fees

exec_time

order (FK id)

account (FK id)

Used by the paper-order APIs to return the created fill alongside the order/account snapshot.

Paper Trading Engine

File: Trades/paper_engine.py 

paper_engine

This module implements the v1 paper trading engine. It simulates fills and updates account/position state using the ActAndPos models:

Account – net liq, cash, buying power

Order – intraday order record

Position – current holdings and P&L

Trade – execution/fill record (from this app)

Key Components
Data classes & errors

PaperOrderParams

account: Account

symbol: str

asset_type: str

side: str (BUY / SELL)

quantity: Decimal

order_type: str (MKT, LMT, STP, STP_LMT)

limit_price: Decimal | None

stop_price: Decimal | None

commission: Decimal = 0

fees: Decimal = 0

Exceptions:

PaperTradingError – base class

InvalidPaperOrder – bad input (side, type, qty, missing limit, etc.)

InsufficientBuyingPower – BP check fails before placing the order

_get_fill_price(params)

V1 logic:

If limit_price is present → use that as the fill price.

Else, uses a stubbed “market” price of 100 (can be replaced with real quotes later).

_validate_params(params)

Enforces:

account.broker == "PAPER"

quantity > 0

side in {"BUY","SELL"}

order_type in {"MKT","LMT","STP","STP_LMT"}

limit_price is required for LMT / STP_LMT orders.

place_paper_order(params: PaperOrderParams)

Main entry point for executing a paper trade. 

paper_engine

Steps (all wrapped in a DB transaction):

Validate parameters

Raises InvalidPaperOrder if anything is wrong.

Lock and load account

Account.objects.select_for_update().get(pk=params.account.pk)

Ensures consistent cash/BP updates under concurrency.

Compute fill price & BP check

fill_price = _get_fill_price(params)

notional = fill_price * quantity

If side == BUY and account.day_trading_buying_power < notional → raises InsufficientBuyingPower.

Create the WORKING Order

New Order row in ActAndPos:

account, symbol, asset_type, side, quantity

order_type, limit_price, stop_price

status = "WORKING"

time_placed = now

Create the Trade (fill)

New Trade row in this app:

account, order, symbol, side, quantity

price = fill_price

commission, fees

exec_time = now

Mark the order as filled:

status = "FILLED"

time_filled = now

time_last_update = now

Update or create Position

Position.objects.select_for_update().get_or_create(...) by (account, symbol, asset_type).

For BUY:

New weighted-average avg_price.

quantity increases.

mark_price set to fill_price.

For SELL:

quantity decreases.

Realized P&L for this leg:

(fill_price - avg_price) * quantity * multiplier

Added to realized_pl_day and realized_pl_open.

mark_price set to fill_price.

Update Account cash & buying power

trade_value = fill_price * quantity * multiplier

total_cost = trade_value + commission + fees

For BUY:

cash -= total_cost

For SELL:

cash += trade_value - (commission + fees)

Recompute net_liq:

net_liq = cash + Σ(position.market_value) for all positions on that account.

Simple v1 BP rules:

stock_buying_power = net_liq * 4

option_buying_power = net_liq * 2

day_trading_buying_power = net_liq * 4

Return

(order, trade, position, account) for the view to serialize.

Paper Trading API

File: Trades/paper_orders.py 

paper_orders

This module exposes REST endpoints for the frontend to place and cancel paper trades.

It uses:

get_active_account(request) from ActAndPos for account selection

AccountSummarySerializer, OrderSerializer, PositionSerializer (from ActAndPos)

TradeSerializer (from Trades)

place_paper_order (from the paper engine)

1. POST /trades/paper/order – Paper trade using active account

View: paper_order_view

Typical mounted path (with project prefix): /api/trades/paper/order.

Request body:

{
  "symbol": "ES",
  "asset_type": "FUT",
  "side": "BUY",
  "quantity": 1,
  "order_type": "MKT",      // or "LMT", "STP", "STP_LMT"
  "limit_price": 4800.25,   // for LMT/STP_LMT
  "stop_price": null
}


Uses get_active_account(request):

Looks at ?account_id= query param, or

Falls back to the default account. (From ActAndPos helper.)

Builds PaperOrderParams.

Calls place_paper_order.

Response (201):

{
  "account": { /* AccountSummarySerializer */ },
  "order": { /* OrderSerializer */ },
  "position": { /* PositionSerializer */ }  // null if no position
}


Used by the Trade workspace ticket as a simple “fire-and-forget” entrypoint.

2. POST /trades/paper/orders – Paper trade with explicit account + snapshot

View: paper_order_create_view

Path: /api/trades/paper/orders

Request body:

Same as above, but requires an account_id field:

{
  "account_id": 3,
  "symbol": "AAPL",
  "asset_type": "EQ",
  "side": "BUY",
  "quantity": "10",
  "order_type": "MKT",
  "limit_price": null,
  "stop_price": null
}


Response (201):

{
  "order": { /* OrderSerializer */ },
  "trade": { /* TradeSerializer */ },
  "account": { /* AccountSummarySerializer */ },
  "positions": [ /* PositionSerializer[] for this account */ ]
}


This is a richer API, returning both the new trade and the updated positions snapshot in one call.

3. POST /trades/paper/orders/<pk>/cancel – Cancel a paper order

View: paper_order_cancel_view

Path: /api/trades/paper/orders/<int:pk>/cancel

Rules:

Looks up Order by pk.

Ensures the linked account.broker == "PAPER".

Only allows cancellation if status == "WORKING":

If not, returns 400 with a message like:
Only WORKING orders can be canceled (current status: FILLED).

On success:

Sets status = "CANCELED".

Sets time_canceled and time_last_update.

Returns the updated Order serialized.

URL Configuration

File: Trades/urls.py 

urls

from django.urls import path

from .paper_orders import (
    paper_order_view,
    paper_order_create_view,
    paper_order_cancel_view,
)

app_name = "Trades"

urlpatterns = [
    path("paper/order", paper_order_view, name="paper-order"),
    path("paper/orders", paper_order_create_view, name="paper-orders-create"),
    path("paper/orders/<int:pk>/cancel", paper_order_cancel_view, name="paper-orders-cancel"),
]


In the project-level urls.py, you typically include:

path("api/trades/", include("Trades.urls", namespace="Trades")),


which yields:

POST /api/trades/paper/order

POST /api/trades/paper/orders

POST /api/trades/paper/orders/<pk>/cancel

Django Admin

File: Trades/admin.py 

admin

TradeAdmin gives you a good view into trade history:

list_display:

account, order, symbol, side, quantity, price, commission, fees, exec_time.

list_filter: side, account

search_fields: by symbol, account display name, broker account ID, exec_id, and order__broker_order_id.

date_hierarchy = "exec_time" for quick date-based navigation.

ordering = ("-exec_time",).

Use this to inspect paper fills, debug trading behavior, or validate P&L.

Frontend Integration (Summary)

The Trade banner tab navigates to /app/trade (React).

The Trade workspace page (Trades.tsx):

Loads the current account snapshot using /actandpos/activity/today.

Renders a paper order ticket that POSTs to /api/trades/paper/order.

On success, it shows a toast and can refresh account/activity state.

The Activity & Positions page (ActivityPositions.tsx) continues to use /actandpos/activity/today for read-only intraday views; it doesn’t know or care that the actual trading is handled by the Trades app