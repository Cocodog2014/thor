ThorTrading – Thinkorswim Live Data Pipeline
1. Overview

This document describes how Thinkorswim live market data flows into ThorTrading and how it’s used:

Thinkorswim (TOS) → RTD formulas in Excel

Excel → Python (xlwings) via poll_tos_excel.py / excel_reader.py

Python → Redis via LiveDataRedis

Redis → Django:

Paper order engine (fill prices for market orders)

WebSockets / Channels (live updates to the UI – ready for use)

The goal is to keep the ThorTrading backend cleanly separated into:

LiveData app – handles ingestion and storage of market data.

ActAndPos (Accounts & Positions) – contains the order engine and account logic.

Trades app – presents HTTP APIs / UI and calls the order engine.

2. High-Level Data Flow
Thinkorswim (TOS)
     │
     │  (RTD formulas)
     ▼
Microsoft Excel (RTD worksheet)
     │
     │  xlwings / Python
     ▼
poll_tos_excel.py  +  excel_reader.py
     │
     │  LiveDataRedis.publish_quote(symbol, quote_dict)
     ▼
Redis
  ├─ live_data:latest:quotes   (hash of latest snapshots)
  └─ live_data:quotes:{symbol} (pub/sub channels per symbol)

     │
     ├─ ThorTrading order engine (fills paper orders via Redis)
     └─ Django Channels / WebSockets (push quotes to browser)

3. Components
3.1. Excel & Thinkorswim RTD

Thinkorswim publishes live quotes into Excel cells via RTD formulas.

The spreadsheet contains one row per symbol with columns like:

Symbol

Last

Bid

Ask

Open, High, Low

Volume, etc.

3.2. Excel Reader (excel_reader.py)

Responsibilities:

Use xlwings to open and read a dedicated Excel workbook.

Convert each row into a standardized Python dict, for example:

{
    "symbol": "VFF",
    "last": "3.00",
    "bid": "2.95",
    "ask": "3.05",
    "open": "2.80",
    "high": "3.10",
    "low": "2.75",
    "volume": "123456",
    ...
}


Handles basic parsing / cleanup of cells.

This is the single source for turning Excel rows → structured quote objects.

3.3. Poller / Management Command (poll_tos_excel.py)

Responsibilities:

Runs as a Django management command (e.g. python manage.py poll_tos_excel).

On each loop:

Reads the spreadsheet via excel_reader.

For each row/symbol, builds a quote_dict.

Calls live_data_redis.publish_quote(symbol, quote_dict).

Can be configured with an interval (e.g. every 1 second).

Long-running process that must be running while you want fresh quotes.

3.4. Redis Client (redis_client.py / LiveDataRedis)

Centralized Redis access, encapsulated in the LiveData app.

Key responsibilities:

Maintain a singleton-like instance live_data_redis with methods such as:

publish_quote(symbol, quote_dict)

set_latest_quote(symbol, quote_dict)

get_latest_quote(symbol)

Under the hood, it:

Publishes each quote to a Pub/Sub channel:

live_data:quotes:{symbol}

Stores a latest-snapshot hash:

Key: live_data:latest:quotes

Field: symbol (e.g. VFF)

Value: JSON-encoded quote dictionary

Result:

Any consumer (order engine, Channels, background tasks) can access:

The most recent quote via get_latest_quote(symbol).

Live streaming updates via subscription to live_data:quotes:*.

4. Redis Data Model
4.1. Latest Quotes Hash

Key: live_data:latest:quotes

Type: Redis hash

Field: SYMBOL (e.g. VFF, ES, AAPL)

Value: JSON string containing last quote, for example:

{
  "symbol": "VFF",
  "last": "3.00",
  "bid": "2.95",
  "ask": "3.05",
  "open": "2.80",
  "high": "3.10",
  "low": "2.75",
  "volume": "123456",
  "timestamp": "2025-12-08T18:30:00Z"
}


Usage:

live_data_redis.get_latest_quote("VFF") → returns the parsed dict.

4.2. Per-Symbol Channels

Channel name: live_data:quotes:{symbol} (e.g. live_data:quotes:VFF)

Each published quote is also pushed to this channel.

Intended consumers:

Django Channels consumers → WebSockets to frontend.

Any other microservice or worker that needs streaming data.

5. Django Channels Integration

The LiveData app already has Channels support wired up:

channels.py defines routing and channel layer configuration.

WebSocket consumers can join groups or channels keyed off symbol names.

When publish_quote is called, it can (if configured) also:

Notify a channel layer group (e.g. quotes:VFF) that a new quote arrived.

Frontend clients subscribed via WebSockets receive data in real time.

This lays the groundwork so the same Redis data used by the order engine can also power a live quote UI.

6. Order Engine Integration (ActAndPos)

The paper order engine lives in the Accounts & Positions app (ActAndPos), not in Trades.

6.1. _get_live_price_from_redis(symbol)

A helper inside order_engine.py:

Calls live_data_redis.get_latest_quote(symbol.upper()).

Extracts a usable price, preferring fields in order:

last

bid

ask

close

Converts the chosen field into a Decimal.

Returns None if:

No quote exists for that symbol.

No usable price field can be parsed.

6.2. _get_fill_price(params: OrderParams)

Core logic for determining the fill price in PAPER mode:

If a limit price is provided (params.limit_price is not None):

Use the limit price as the fill price.

If order type is MKT and no limit:

Call _get_live_price_from_redis(params.symbol).

If a price is returned → use it.

If None → raise InvalidPaperOrder with a clear error:

e.g. “Cannot fill market order: no live market price available…”

For any other order type that needs a price but has no limit:

Reject the order in PAPER mode as unsupported.

This ensures:

Market orders never guess a fake price.

If Thinkorswim / Excel / Redis is running and has the symbol:

The trade is filled at the real-time price.

If the symbol has no quote (not in the Excel list):

The market order is rejected instead of silently filling at 100 or 0.

7. Account & Position Rules (Cash-Only Behavior)

Current design (as of this MD):

Cash account only, no margin, no short selling.

7.1. Buying Power

After each order is processed:

account.cash and positions are updated.

account.net_liq = account.cash + total_market_value.

Buying-power fields are set to cash:

stock_buying_power = account.cash

option_buying_power = account.cash

day_trading_buying_power = account.cash

No leverage multipliers are used (no 4× / 2× margin).

7.2. No Short Selling

In the position update logic for SELL orders:

If position.quantity <= 0 → reject the order (no existing long).

If sell_quantity > position.quantity → reject the order.

Result: quantity can never go negative → no shorts.

Later, this can be extended with an allow_short flag on Account to differentiate cash vs. margin accounts.

8. Trades App Responsibilities

The Trades app does not talk directly to Redis or LiveData.

Its responsibilities:

Expose HTTP endpoints for placing orders (e.g. /api/trades/orders/active).

Parse and validate incoming JSON (symbol, side, quantity, order_type, etc.).

Call place_order(params) from ActAndPos.services.order_engine.

Return the engine’s result (account snapshot, order, position) as JSON.

The engine (ActAndPos) is the one that:

Looks up live prices via LiveData / Redis.

Enforces cash / margin / short-selling rules.

9. Running the Live Data Stack

To have fully functional live data:

Start Redis (already part of your Docker stack).

Run the LiveData poller:

python manage.py poll_tos_excel --interval 1


Ensure the Excel RTD workbook is open and connected to Thinkorswim.

ThorTrading now:

Uses Redis prices to fill market orders in PAPER mode.

Can (optionally) push live quotes over WebSockets to the UI.

10. Future Enhancements

Add margin_enabled / allow_short flags on Account to support real margin simulation.

Add explicit symbol whitelist sourced from Excel so only those symbols are tradable via market orders.

Implement WebSocket consumers for:

Live quote tiles

Blinking “last price” updates in the UI

Add historical snapshot logging (e.g. append quotes to a time-series store / Redis stream for charts).