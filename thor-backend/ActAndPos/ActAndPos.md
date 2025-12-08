ActAndPos – Accounts, Orders, Positions, and the Unified Order Engine (Updated)

ThorTrading Core: Live Account Snapshot + Order Routing + Position Management

ActAndPos is the backend service powering:

Live account view

Intraday orders

Position updating

Real-time P&L

Broker-agnostic order routing (PAPER + SCHWAB + future brokers)

This app no longer contains paper-order APIs or statements (those live in the Trades app).
Instead, ActAndPos is the book of record for:

Accounts

Orders

Positions

The unified execution engine (order_engine.py)

Updated Architecture
          Trades App (User-facing)
         ─────────────────────────
         /orders/active
         /orders           → Calls →  order_engine.place_order()
         /orders/<id>/cancel

             ▲
             │
             ▼

ActAndPos App (Ledger + Engine)
────────────────────────────────
Accounts     ← Database of real/paper accounts
Orders       ← Intraday instructions
Positions    ← Updated after fills
order_engine ← Routes orders to PAPER / SCHWAB adapters


ActAndPos now cleanly owns the truth:

What accounts exist

What positions exist

What today’s orders are

How orders update accounts and positions

Trades owns:

Trade history (fills)

Statements

User-facing “place order” endpoints

Data Model
Account

Represents a real Schwab or Paper account.

Important fields:

broker — "SCHWAB" or "PAPER"

net_liq, cash

stock_buying_power, option_buying_power, day_trading_buying_power

current_cash, equity

updated_at

Property:

ok_to_trade → true when account has positive net liq & buying power

Accounts are updated only via the execution engine.

Order

Intraday order record.

Fields:

account

symbol, asset_type

side → BUY / SELL

order_type → MKT / LMT / STP / STP_LMT

quantity, limit_price, stop_price

status → WORKING, FILLED, CANCELED, PARTIAL, REJECTED

time_placed, time_filled, time_canceled, time_last_update

Orders represent intent, not fills.
Fills live in the Trades app as Trade objects.

Position

One row per (account, symbol, asset_type).

Fields:

quantity, avg_price, mark_price

realized_pl_open, realized_pl_day

multiplier (ES=50, CL=1000, EQ=1)

Computed:

market_value

cost_basis

unrealized_pl

pl_percent

Positions are automatically updated by the order engine.

Execution Engine – order_engine.py (Updated)

ActAndPos now contains the unified order routing engine.

OrderParams

A broker-agnostic dataclass:

@dataclass
class OrderParams:
    account: Account
    symbol: str
    asset_type: str
    side: str
    quantity: Decimal
    order_type: str
    limit_price: Decimal|None
    stop_price: Decimal|None
    commission: Decimal
    fees: Decimal


This single structure is used for all brokers.

Routing Layer
def place_order(params: OrderParams):
    adapter = _get_adapter_for_account(params.account)
    return adapter.place_order(params)

Adapters:

PaperBrokerAdapter

Calls _place_order_paper

Instantly fills the order

Creates Order, Trade, updates Position & Account

SchwabBrokerAdapter (stub)

Validates Schwab account

Prepares payload for Schwab’s API

Will later poll Schwab fills and update Position/Account

This makes brokers pluggable without touching business logic.

Paper Execution Logic (summarized)

Inside _place_order_paper:

Validate params

Lock account row

Determine fill price

Create WORKING Order

Create Trade (fill)

Update Order → FILLED

Update Position:

BUY → increase qty, recalculated avg_price

SELL → decrease qty, record realized P/L

Update Account:

cash

net_liq

buying power fields

Returns: (Order, Trade, Position, Account)

Schwab Path (stub)

Inside _place_order_schwab:

Ensures correct broker

Outlines steps for:

building Schwab API payload

sending order

storing broker_order_id

waiting for fills

applying fills to Account & Position

Currently raises NotImplementedError as a safety guard.

Serializers
AccountSummarySerializer

Minimal view of an account:

net_liq, cash

buying power

ok_to_trade

OrderSerializer

Intraday order details.
Used by /actandpos/activity/today.

PositionSerializer

UI-ready position attributes + computed P/L.

Views & Endpoints (ActAndPos)
GET /actandpos/activity/today

Returns:

account summary

today’s working orders

today’s filled orders

today’s canceled orders

current positions

account status (ok_to_trade, buying power, etc.)

This powers the Activity & Positions page.

GET /actandpos/positions

Positions + account snapshot without orders.
Used for analytics pages.

Relationship to Trades App
Feature	Lives In	Reason
Orders (intent)	ActAndPos	Ledger model
Positions	ActAndPos	Live holdings
Accounts	ActAndPos	Book of record
Fills (Trade)	Trades	Execution history
Statements	Trades	User-facing reporting
UI order creation APIs	Trades	Frontend integration
Order Execution Engine	ActAndPos	Core business logic

The Trades app calls ActAndPos’s place_order but does not implement execution logic itself.

Future Extensions

ActAndPos will expand with:

Broker-agnostic snapshot caching

Risk metrics (exposure, leverage, correlations)

Intraday margin and PDT rules

Broker heartbeat / account status tracking

Trades app expands with:

Fill polling for Schwab

Historical reporting

Option strategy statements