Trades – Executions, Paper Trading Engine, & Account Statements (Updated)

ThorTrading Trading Layer

The Trades app owns everything related to executions, fills, paper trading logic, and now account statements.

ActAndPos handles “What do I have right now?”
Trades handles “What did I do?” and “Do a trade now.”

Trades depends on ActAndPos for:

Accounts

Orders

Positions

ActAndPos does not depend on Trades.

Trade

App Overview

Django app: Trades

Trade rows stored in legacy table ActAndPos_trade (backward compatible)

Integrates with ActAndPos through:

Account (for balances and buying power)

Order (status: WORKING → FILLED)

Position (qty/price/P&L updates)

Exposes:

Paper trading APIs

Trade history

Account Statement API (new)

Core Responsibilities
Trades App does:

Create fills (Trade rows)

Update Positions & Account balances

Recompute P&L & buying power

Validate orders, BP, sizes

Provide trade history

Provide Account Statements reporting endpoint

Trades App does NOT:

Hold live positions (ActAndPos does that)

Hold account balances (ActAndPos)

Pull market data (stub only)

Own intraday orders (ActAndPos)

1. Data Model – Trade

Defined in Trades/models.py.


Trade

Represents a single execution (fill), submitted by the paper engine or a real broker sync (future).

Key Fields

account – FK → ActAndPos.Account

order – FK → ActAndPos.Order (related_name="trades")

symbol

side – BUY / SELL

quantity

price

commission, fees

exec_time

exec_id

Meta

ordering = ("-exec_time",)

db_table = "ActAndPos_trade" (backward compatibility)

Purpose

Trade is the “ledger” of everything the user did, and is the backbone of:

P&L

Statements

Execution history

Analytics

2. Serializers

TradeSerializer


Trade

Fields exposed to the frontend:

id

symbol

side

quantity

price

commission

fees

exec_time

account id

order id

Used by:

Paper trade responses

Account statements (trade history section)

3. Paper Trading Engine

Located in Trades/paper_engine.py.


Trade

The engine simulates a complete lifecycle:

Validate order

Check buying power

Create working order

Create fill (Trade)

Update position

Update account balances

Recompute net liq + BP

Return a full snapshot

Data Classes and Errors

PaperOrderParams

PaperTradingError

InvalidPaperOrder

InsufficientBuyingPower

Fill Price Logic

LMT / STP_LMT → use limit price

Others (MKT/STP) → stubbed price of 100 (to be replaced)

Position Updates

BUY:

Increase quantity

Recompute weighted average price

Update realized P&L fields if closing short

SELL:

Decrease quantity

Calculate realized P&L

Update realized_pl_day & realized_pl_open

Account Updates

Adjust cash

Adjust BP (simple v1 rules)

Recompute net_liq based on all positions

The engine returns:

(order, trade, position, account)

4. Paper Trading API

Located in Trades/paper_orders.py.


Trade

All endpoints use:

get_active_account() from ActAndPos

Serializers from ActAndPos (AccountSummary, Order, Position)

TradeSerializer from Trades

POST /trades/paper/order

Simple entrypoint → uses active account

Input

Symbol, asset_type, side, quantity, order_type, limit/stop

Output

account summary

order

resulting position

POST /trades/paper/orders

Advanced entrypoint → requires account_id

Output

order

trade

account summary

updated positions list

POST /trades/paper/orders/<id>/cancel

Cancels WORKING orders only.

5. Account Statements API (NEW)

(This is now part of the Trades app.)

Purpose

Provide the data for the React Account Statements page:

Date-range trade history

Current positions snapshot

P&L summary

Buying power summary

Symbol filters & search filters

Why it lives in Trades

Because statements depend on Trade history, which exists only here.

ActAndPos → live snapshot
Trades → historical ledger + reporting

Endpoint (planned/active depending on your branch)
GET /api/trades/account-statement

Query Params

account_id (optional)

days_back=1
or

from=YYYY-MM-DD & to=YYYY-MM-DD

Response Shape
{
  account: AccountSummary,
  date_range: { from, to },

  cashSweep: [],
  futuresCash: [],

  equities: [...],        // from ActAndPos.Position
  pnlBySymbol: [...],     // computed from Position

  trades: [...],          // TradeSerializer rows (in date range)

  summary: [...],         // BP, cash, net liq, etc.
}

6. FLOW: ActAndPos → Trades (Execution Flow)

Here’s the complete lifecycle showing how the two apps cooperate.

STEP 1 — Frontend requests a trade

React →

POST /api/trades/paper/order

STEP 2 — Trades chooses the correct account

Trades asks ActAndPos:

get_active_account(request)


or via direct account_id.

STEP 3 — Trades validates & processes order

Trades engine needs:

Account (ActAndPos)

Position (ActAndPos)

Order (ActAndPos)

Trade (Trades)

STEP 4 — Trades updates ActAndPos models

In the DB transaction:

Create/update Order

Create/update Position

Update Account fields:

cash

net liq

buying powers

ActAndPos is the source of truth for balances & holdings.

STEP 5 — Trades creates the Trade (fill)

Writes a new Trade row to ActAndPos_trade.
(This is historical record for reporting & statements.)

STEP 6 — Trades returns updated snapshot

Response includes:

Account summary

Order

Trade

Current position(s)

STEP 7 — React updates UI

Activity & Positions repolls /api/actandpos/activity/today

Account Statements queries /api/trades/account-statement

7. Django Admin

TradeAdmin exposes:

trades list

filters by side/account

search by symbol, exec_id, order info

date hierarchy for exec_time

Used for debugging and reviewing fills.

8. Frontend Integration Overview
UI Page	Endpoints Used	Purpose
Trade Workspace	/api/trades/paper/order	Create trades
	/api/actandpos/activity/today	Refresh snapshot
Activity & Positions	/api/actandpos/activity/today	Intraday orders + positions
Account Statements	/api/trades/account-statement	Historical + snapshot reporting
In Summary

ActAndPos = live data (accounts, orders, positions)

Trades = actions + history + reporting

Trades now cleanly owns everything transactional:

Executions

Trade history

P&L events

Statements

Paper engine

ActAndPos owns current state and remains clean.