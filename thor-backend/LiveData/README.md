# LiveData — single guide

Simple, provider-agnostic live data pipeline for Thor. LiveData fetches from brokers (TOS, Schwab, etc.), publishes to Redis, and exposes a uniform HTTP snapshot for any app to consume. Business apps never talk to brokers directly.

This README replaces ARCHITECTURE.md and MIGRATION.md.

## Architecture diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         External data sources                        │
├──────────────────────────────────────────────────────────────────────┤
│  TOS Excel / Stream      Schwab Trading API        (Future) IBKR     │
└───────────────┬────────────────────┬───────────────────────┬─────────┘
                │                    │                       │
                ▼                    ▼                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                             LiveData                                 │
├──────────────────────────────────────────────────────────────────────┤
│  tos/ (excel_reader, views)      schwab/ (oauth, services)           │
│                                  shared/ (redis_client, channels)    │
│                                  → publish_quote(symbol, payload)    │
└───────────────┬──────────────────────────────────────────────────────┘
                │
                │ publish JSON + cache latest
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                               Redis                                  │
├──────────────────────────────────────────────────────────────────────┤
│ Pub/Sub channels:                                                    │
│   live_data:quotes:{SYMBOL}  (streaming)                             │
│   … positions/balances/orders/transactions                           │
│ Snapshot cache (hash):                                               │
│   live_data:latest:quotes  → field: SYMBOL → JSON payload            │
└───────────────┬──────────────────────────────────────────────────────┘
                │                           │
                │ HTTP (seed page)          │ Redis (live updates)
                ▼                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         Business / UI apps                           │
├──────────────────────────────────────────────────────────────────────┤
│  FutureTrading (backend)  account_statement  thor-frontend (UI)      │
│  - GET /api/feed/quotes/snapshot?symbols=…                           │
│  - Subscribe live_data:quotes:{SYMBOL}                                │
└──────────────────────────────────────────────────────────────────────┘
```

## What it does

- Ingests from providers (TOS Excel/stream, Schwab API, …)
- Publishes to Redis pub/sub channels
- Stores the latest value per symbol as a snapshot in Redis
- Serves a thin HTTP endpoint to retrieve the latest snapshot for multiple symbols at once

## Folder map

```
LiveData/
  shared/
    channels.py        # Channel naming helpers
    redis_client.py    # Publisher + snapshot cache (live_data_redis)
    urls.py, views.py  # Provider-agnostic endpoints (quotes/snapshot)
  tos/
    excel_reader.py    # Generic Excel reader (TOS RTD ranges)
    services.py        # Streamer (future), helpers
    urls.py, views.py  # TOS-specific endpoints
  schwab/
    models.py, tokens.py, services.py, urls.py, views.py
```

## Data flow

1) Provider receives/reads a quote (e.g., TOS Excel row or WebSocket event)
2) Provider calls `live_data_redis.publish_quote(symbol, payload)`
   - Publishes JSON to `live_data:quotes:{SYMBOL}`
   - Caches the latest payload in hash `live_data:latest:quotes`
3) Apps get data by either:
   - Subscribing to Redis channel(s) for streaming; or
   - Calling the snapshot HTTP endpoint for quick page loads.

## Contracts

### Redis channels
- Quotes: `live_data:quotes:{symbol}`
- Positions: `live_data:positions:{account_id}`
- Balances: `live_data:balances:{account_id}`
- Orders: `live_data:orders:{account_id}`
- Transactions: `live_data:transactions:{account_id}`

Payloads are JSON (numbers/decimals serialized via `default=str`). Quote payload includes at minimum:

```
{
  "type": "quote",
  "symbol": "ES",
  "bid": 4712.25,
  "ask": 4712.50,
  "last": 4712.25,
  "volume": 123456,
  "timestamp": "2025-10-24T14:33:12Z"
}
```

### Snapshot cache (Redis)
- Key: `live_data:latest:quotes` (hash)
- Field: SYMBOL → JSON payload (same shape as above)
- Writers: any provider calling `publish_quote()`
- Readers: snapshot endpoint (or direct Redis reads if you prefer)

## HTTP endpoints

- Provider-agnostic snapshot:
  - `GET /api/feed/quotes/snapshot/?symbols=YM,ES,NQ,RTY,CL,SI,HG,GC,VX,DX,ZB`
  - Response:
    ```
    {
      "quotes": [ { ...payload... }, ... ],
      "count": 11,
      "source": "redis_snapshot"
    }
    ```

- TOS Excel reader (optional bootstrap/testing):
  - `GET /api/feed/tos/quotes/latest/?consumer=futures_trading&file_path=A:\\Thor\\CleanData.xlsm&sheet_name=Futures&data_range=A1:M12`
  - Returns raw rows and also publishes each row to Redis (which updates the snapshot).

## Integrating another app (consumer)

Two options—use both if you want fast initial load + live updates:

1) Initial load (HTTP):
   - Call `/api/feed/quotes/snapshot/?symbols=...`
   - Render UI immediately with latest values.

2) Live updates (Redis):
   - Subscribe to `live_data:quotes:{symbol}` for each symbol you care about.
   - Apply updates as messages arrive.

Minimal Python example:

```python
import json, redis, requests

symbols = ["YM","ES","NQ"]
# a) Snapshot
resp = requests.get("http://localhost:8000/api/feed/quotes/snapshot/", params={"symbols": ",".join(symbols)})
print(resp.json()["quotes"])  # Seed your UI

# b) Streaming
r = redis.Redis()
ps = r.pubsub()
ps.subscribe(*[f"live_data:quotes:{s}" for s in symbols])
for msg in ps.listen():
    if msg["type"] == "message":
        data = json.loads(msg["data"])  # apply to UI/state
```

## Adding a new provider (publisher)

Create a new app or extend an existing provider and, when you have a quote payload, call:

```python
from LiveData.shared.redis_client import live_data_redis
live_data_redis.publish_quote(symbol, payload)
```

That’s it—your data will stream and snapshot uniformly for all consumers.

## Environment

Redis settings come from Django settings with defaults:
- `REDIS_HOST` (default `localhost`)
- `REDIS_PORT` (default `6379`)
- `REDIS_DB`   (default `0`)

## Troubleshooting

- Snapshot empty? Make sure at least one publisher has called `publish_quote()` recently (or hit the TOS Excel reader endpoint once to seed).
- Mixed symbol formats? We recommend stripping the leading slash and uppercasing (`/ES` → `ES`).
- Decimals/Datetime serialization issues? We use `json.dumps(..., default=str)` in the publisher.

## Migration note

Older documents (architecture & migration) are now merged here. The high-level design remains: LiveData publishes; business apps consume.
4. ⏳ Implement TOS WebSocket connection (`LiveData/tos/services.py`)
5. ⏳ Refactor `FutureTrading/views.py` to subscribe to Redis
6. ⏳ Add IBKR integration (when needed)

---

**Questions?** Check the code in `LiveData/shared/redis_client.py` for usage examples.
