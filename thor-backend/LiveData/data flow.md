Big picture: 3 roles
GlobalMarkets = the clock + rules

Knows what markets exist

Knows open/close times + timezone + holidays

Knows enable flags (enable_session_capture, etc.)

Emits: market opened / market closed events

LiveData = ingestion

Connects to TOS Excel poller and/or Schwab streaming

Publishes ticks/quotes into Redis (shared bus)

Does not decide sessions/market hours (keep it dumb + reliable)

ThorTrading = the engine

Uses GlobalMarkets to decide which markets are active

Uses Redis ticks to build:

intraday 1m bars

session / 24h / 52w metrics

Persists intraday + summary tables to Postgres

The data flow sketch (ASCII map)
           ┌───────────────────────────────┐
           │           GlobalMarkets        │
           │  - market hours + tz + flags   │
           │  - determines OPEN/CLOSED      │
           │  - emits open/close events     │
           └───────────────┬───────────────┘
                           │ (market state + triggers)
                           ▼
┌───────────────────────────────────────────────────────────┐
│                        ThorTrading                          │
│  "Engine": decides what to process + builds bars/metrics    │
│                                                           │
│   ┌──────────────┐     ┌──────────────┐    ┌────────────┐ │
│   │ Intraday Sup │ --> │ Bar Queue/DB │ -> │ Postgres     │ │
│   │ (1-min bars) │     │ Flusher      │    │ Intraday tbl │ │
│   └──────┬───────┘     └──────┬───────┘    └────────────┘ │
│          │                    │                             │
│          │ publishes/reads     │ writes summaries            │
│          ▼                    ▼                             │
│   ┌──────────────┐    ┌──────────────┐   ┌──────────────┐ │
│   │ Session Sup  │    │ 24h Sup       │   │ 52w Sup       │ │
│   │ (session OHL │    │ (rolling 24h) │   │ (rolling 52w) │ │
│   └──────────────┘    └──────────────┘   └──────────────┘ │
└───────────────────────────────────────────────────────────┘
                           ▲
                           │ (ticks/quotes in Redis)
           ┌───────────────┴───────────────┐
           │             Redis              │
           │   shared bus + state + queues  │
           └───────────────┬───────────────┘
                           ▲
                           │ writes ticks
                   ┌───────┴────────┐
                   │    LiveData     │
                   │ ingestion layer │
                   │ - TOS poller    │
                   │ - Schwab stream │
                   └─────────────────┘

What actually happens minute-by-minute
A) LiveData: “always collecting”

Every tick (or every Excel poll cycle):

Read price update from TOS/Schwab

Write to Redis:

tick:{symbol} or tick:{country}:{symbol}

Optionally publish:

pubsub:tick event

That’s it. No market logic.

B) GlobalMarkets: “always deciding”

On its heartbeat / scheduler:

Computes market status (open/closed)

If status changed:

emits market_opened(USA), market_closed(Japan), etc.

It doesn’t touch prices.

C) ThorTrading intraday supervisor: “build bars only for active markets”

Every second (or every minute boundary) it does:

Ask GlobalMarkets:

“Which markets are open + enabled right now?”

For each open market:

get list of symbols in that market

read each symbol’s latest tick from Redis

build/update the 1-minute bar in Redis using UTC minute buckets:

bar:1m:current:{country}:{symbol}

If a minute just closed:

enqueue the closed bar:

q:bars:1m:{country}

A DB worker flushes that queue:

writes rows into Postgres intraday table

✅ Result: Postgres intraday table is a durable “minute history”
✅ Redis always has “current minute bar” + a backlog of closed bars to flush

Where session / 24h / 52w fit in
Session supervisor

Consumes the same bar events / latest bars in Redis

Maintains rolling session values in Redis:

session:{country}:{symbol}:state

When GlobalMarkets emits market_closed (or session ends):

write one “final session row” in Postgres

24h supervisor

Also consumes bar updates

Maintains rolling 24h window metrics in Redis

Writes a summary row periodically or at boundary

52-week supervisor

Updates highs/lows when a new bar comes in

Writes only when high/low changes (plus optional nightly checkpoint)

The “control” answer in one line

GlobalMarkets controls whether ThorTrading runs for a market

LiveData feeds Redis regardless

ThorTrading consumes Redis only for open/enabled markets

So it’s not:

GlobalMarkets sends data to ThorTrading

It’s:

GlobalMarkets tells ThorTrading what to pay attention to.