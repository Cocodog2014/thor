Trades App – Trade Fills, Statements, and User-Facing Order APIs

ThorTrading – Updated Architecture Documentation

The Trades app is the user-facing trading layer of Thor.
It no longer contains execution logic — the execution engine now fully lives inside ActAndPos.

Instead, Trades is responsible for:

Exposing API endpoints to create/cancel orders

Storing Trade (fill) records

Building account statements

Returning snapshots that the frontend uses

Trades is the bridge between the UI and the ActAndPos ledger.

🔥 High-Level Architecture
Frontend (React / TSX)
        │
        ▼
Trades App (User-facing APIs)
 - /orders/active
 - /orders
 - /orders/<id>/cancel
 - /account-statement
        │
        ▼
ActAndPos (Ledger + Engine)
 - Accounts
 - Orders
 - Positions
 - order_engine (PAPER + SCHWAB adapters)


The frontend never talks to ActAndPos directly.
All order requests go through the Trades app, which validates them, then hands them to the unified engine.

📌 Models in Trades
Trade (Fill Model)

Each execution/fill of an order becomes one Trade row.

Stored fields typically include:

account

order

symbol

side

quantity

price

commission

fees

exec_time

This model does not store order intent — only actual fills.

It exists separately from ActAndPos.Order for correct ledger separation.

📌 Views in Trades
1. Order Creation Views
order_create_active_view
POST /trades/orders/active


Creates an order for the active account (session or ?account_id).

Flow:

Validate user input

Build OrderParams

Call place_order() in ActAndPos.order_engine

Engine creates:

Order

Trade (fill)

Position update

Account update

Trades returns a clean snapshot to the UI

Use case:
The frontend Quick Ticket (single active account mode).

order_create_view
POST /trades/orders


Creates an order for a specific account_id.

Used by:

Multi-account dashboards

Server-side processes

Admin / batch simulation

2. Order Cancel Endpoint
order_cancel_view
POST /trades/orders/<pk>/cancel


Cancels a WORKING order.

Right now only PAPER supports cancelation (Schwab is stubbed).

The view updates:

Order.status → CANCELED

time_canceled

time_last_update

Positions/cash are untouched.

3. Account Statements
account_statement_view
GET /trades/account-statement


Generates a human-readable trading statement for the selected account:

All Trade (fills) history

Current Position list

Account summary (from ActAndPos)

P&L breakdown

Totals and daily aggregates

This is a read-only reporting layer — it never modifies ledger data.

Statements correctly combine:

ActAndPos models (Accounts, Positions)

Trades model (Trade fills)

📌 Serializers

Trades uses:

TradeSerializer (internal to Trades)

AccountSummarySerializer (from ActAndPos)

OrderSerializer and PositionSerializer (from ActAndPos)

This reinforces the separation:

ActAndPos owns ledger data

Trades presents it to the UI

📌 URL Structure (Updated & Clean)
urlpatterns = [
    path("orders/active", order_create_active_view, name="orders-create-active"),
    path("orders", order_create_view, name="orders-create"),
    path("orders/<int:pk>/cancel", order_cancel_view, name="orders-cancel"),
    path("account-statement", account_statement_view, name="account-statement"),
]


These URLs are neutral — not PAPER-specific — because orders now route through the unified engine.

📌 Responsibilities Summary
Component	Lives In	Description
Order model	ActAndPos	Intent to trade
Position model	ActAndPos	Current holdings
Account model	ActAndPos	Cash, net liq, buying power
Execution engine	ActAndPos	PAPER & SCHWAB adapters
Trade (fill) model	Trades	Execution events
Order-create APIs	Trades	User entry + validation
Statements	Trades	Reporting, not ledger
📌 Why This Split Matters

This structure matches real broker systems like:

Thinkorswim

Interactive Brokers

TradeStation

They all separate:

Ledger (accounts, positions, orders)

Execution reports (fills)

User APIs (order entry, reporting)

You are now aligned with real brokerage architecture — which means:

Scalable

Safe

Easy to extend

Easy to plug in new brokers (Schwab → IBKR → crypto, etc.)

📌 Future Expansion

Trades app can later include:

WebSocket streaming for real-time order/position updates

Trade analytics (win% / expectancy / drawdown)

Option strategy statements

Multi-account switching & routing

Commission models

All without modifying ActAndPos.