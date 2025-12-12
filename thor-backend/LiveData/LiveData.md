LiveData — Unified Real-Time Market Data Layer

LiveData pulls real-time market data from multiple brokers/providers (TOS RTD Excel, Schwab Trading API, etc.), publishes structured updates into Redis, and exposes simple HTTP endpoints that business apps can consume without needing to talk to brokers directly.

This is the single authoritative document for how LiveData works.

Architecture Diagram
┌─────────────────────────────────────────────────────────────────────────┐
│                          External Data Sources                          │
├─────────────────────────────────────────────────────────────────────────┤
│  TOS Excel RTD        Schwab REST API (OAuth)       (Future) IBKR API   │
└───────────────┬───────────────────────┬──────────────────────┬──────────┘
                │                       │                      │
                ▼                       ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                                LiveData                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  tos/                                                                    │
│    - excel_reader.py  → read RTD ranges (generic reader)                 │
│    - views.py         → /tos/quotes/latest, subscribe/unsubscribe        │
│    - poll_tos_excel.py → bg polling daemon (optional)                    │
│                                                                          │
│  schwab/                                                                 │
│    - models.py (BrokerConnection storage)                                │
│    - views.py   (OAuth redirects, account list, positions, balances)     │
│    - services.py (SchwabTraderAPI wrapper)                               │
│                                                                          │
│  shared/                                                                  │
│    - redis_client.py  (publish_quote, excel locks, snapshot caching)     │
│    - channels.py      (Redis key naming)                                │
│                                                                          │
│  → All providers call live_data_redis.publish_quote(payload)             │
└───────────────┬──────────────────────────────────────────────────────────┘
                │
                │ publish JSON + update snapshot
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                                   Redis                                  │
├─────────────────────────────────────────────────────────────────────────┤
│ Pub/Sub                                                                  │
│   live_data:quotes:{SYMBOL}     → per-symbol streaming                    │
│   live_data:positions:{acct}                                             │
│   live_data:balances:{acct}                                              │
│                                                                          │
│ Snapshot cache (HASH)                                                    │
│   live_data:latest:quotes → field=SYMBOL → last JSON payload             │
└───────────────┬──────────────────────────────────────────────────────────┘
                │                         │
                │ HTTP snapshot           │ Redis streaming
                ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            Business / UI Apps                           │
├─────────────────────────────────────────────────────────────────────────┤
│ FutureTrading, Thor-Frontend, AccountStatement, etc.                    │
│   - GET /api/feed/quotes/snapshot/                                      │
│   - Subscribe live_data:quotes:{symbol}                                 │
└─────────────────────────────────────────────────────────────────────────┘

What LiveData Does

Reads real-time quotes from:

TOS Excel RTD

Schwab Trading API

(Future) IBKR, Polygon, Tradier, etc.

Publishes every update to Redis:

Pub/Sub channels for streaming UI

Snapshot hash for instant loads

Acts as a broker-agnostic façade:

No business app should ever talk directly to Schwab, Excel, or IBKR

They all talk to LiveData only

Folder Map (Accurate to Your Code)
LiveData/
  shared/
    channels.py        # Unified Redis key/channel naming
    redis_client.py    # publish_quote, locks, snapshots

  tos/
    excel_reader.py    # xlwings RTD reader (generic)
    poll_tos_excel.py  # Management command: continuous Excel->Redis polling
    views.py           # HTTP: status, subscribe, unsubscribe, latest quotes
    urls.py

  schwab/
    models.py          # BrokerConnection (OAuth storage)
    tokens.py          # Token refresh helpers
    services.py        # SchwabTraderAPI (fetch accounts, positions, balances)
    views.py           # OAuth redirect, account summary, positions, balances
    urls.py

Data Flow (Detailed)
1. Provider gets new data

Examples:

TOS Excel row changes

Schwab REST /v1/accounts/{id}/positions response

(Future) IBKR WebSocket tick

2. Provider calls
live_data_redis.publish_quote(symbol, payload)


This performs three things:

Publishes to:

live_data:quotes:{SYMBOL}


Writes snapshot into hash:

live_data:latest:quotes[SYMBOL] = JSON


Normalizes & serializes numeric/datetime fields.

3. Consumer apps

Subscribe to streaming channels

OR call:

GET /api/feed/quotes/snapshot/?symbols=ES,NQ,CL,GC

TOS Provider (LiveData/tos)
excel_reader.py

Provides a generic TOSExcelReader class:

Connect/disconnect workbook

Read ranges sheet_name + data_range

Parse decimals, bond fractions, blank cells

Outputs clean Python dicts for each row

Supports both:

On-demand fetch (get_latest_quotes)

Long-running polling (poll_tos_excel)

poll_tos_excel.py — Background Poller

Command: python manage.py poll_tos_excel

Options:

--file, --sheet, --range, --interval

Uses:

excel_lock → prevents simultaneous Excel access

Calls publish_quote() for each row

Intended for production continuous streaming

views.py — TOS HTTP Control Plane

Endpoints:

GET /tos/status/

Shows:

Stream connected state

Current subscribed symbols

POST /tos/subscribe/

Adds symbol to streamer's subscription list

Publishes updates as they come

POST /tos/unsubscribe/

Removes a symbol from streamer

GET /tos/quotes/latest/

Reads Excel once (no long-running loop)

Publishes each quote to Redis

Returns cleaned rows as JSON

Useful for:

Debug

Cold-start snapshot

Apps like FutureTrading

Schwab Provider (LiveData/schwab)
models.py — BrokerConnection

Stores:

access_token

refresh_token

access_expires_at

Metadata like schwab_account_id

One row per Django user.

views.py — OAuth & Data Fetching
GET /schwab/oauth/start/

Redirects user to Schwab login page.

GET /schwab/oauth/callback/

Stores OAuth tokens in BrokerConnection.

GET /schwab/accounts/

Fetches account list from Schwab API.

GET /schwab/accounts/<id>/positions/

Publishes positions to Redis under:

live_data:positions:{account_id}

GET /schwab/accounts/<id>/balances/

Publishes balances to Redis.

GET /schwab/account/summary/

Returns summary block used by Thor’s UI:

BP

Net Liq

Cash balance

Margin balance

services.py — SchwabTraderAPI

Implements:

Token management

Account list

Positions

Balances

Account summary

Does not store trading data — only fetches and publishes.

Shared Layer (LiveData/shared)
channels.py

Canonical channel naming:

live_data:quotes:{symbol}
live_data:balances:{account_id}
live_data:positions:{account_id}
live_data:orders:{account_id}

redis_client.py

Core of the whole system.

Provides:

Publishers
publish_quote(symbol, payload)
publish_positions(account_id, payload)
publish_balances(account_id, payload)

Snapshot Cache
live_data:latest:quotes


Used by snapshot HTTP API & initial page load.

Excel Lock

Prevents two processes from opening the same Excel workbook:

acquire_excel_lock()
release_excel_lock()


This protects the RTD feed from corruption.

HTTP Endpoints Summary
Provider-Agnostic Snapshot
GET /api/feed/quotes/snapshot/?symbols=ES,NQ,CL


Returns:

{
  "quotes": [...],
  "count": 3,
  "source": "redis_snapshot"
}

TOS Endpoints

/api/feed/tos/status/

/api/feed/tos/subscribe/

/api/feed/tos/unsubscribe/

/api/feed/tos/quotes/latest/

Schwab Endpoints

/schwab/oauth/start/

/schwab/oauth/callback/

/schwab/accounts/

/schwab/accounts/<id>/positions/

/schwab/accounts/<id>/balances/

/schwab/account/summary/

Adding a New Provider

To integrate a new broker/feed:

Create LiveData/<provider>/

Implement:

data fetcher

a view or command

For each update:

live_data_redis.publish_quote(symbol, payload)


Optional:

publish balances, positions, orders

Snapshot + streaming become available system-wide instantly.

Environment & Settings

Redis settings come from Django settings or defaults:

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB   = 0


Excel paths, sheet names, and ranges are supplied by consumers, not by LiveData (making it provider-agnostic).

Troubleshooting
Excel fails to open?

Only one reader may run:

Make sure excel_lock is free

Ensure xlwings installed and Excel open

No quotes updating?

Ensure a poller or /tos/quotes/latest/ hit has run

Ensure providers are actually calling publish_quote()

Token expired?

BrokerConnection.is_expired helps detect

services.exchange_code_for_tokens() refreshes tokens

Status

LiveData supports:

✔ TOS Excel real-time quotes
✔ TOS one-shot fetch
✔ Redis snapshot system
✔ Schwab OAuth & basic account/positions/balances
✔ Provider-agnostic feed interface

Planned:

⏳ Schwab trade placement
⏳ Schwab order updates → Redis
⏳ IBKR or other brokers
⏳ TOS WebSocket (instead of Excel RTD)