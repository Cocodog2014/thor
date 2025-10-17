# LiveData Architecture

**Simple, flexible, multi-broker live market data pipeline for Thor.**

---

## Overview

`LiveData/` is a Django package that fetches and streams live market data from multiple brokers (Schwab, TOS, IBKR, etc.) and publishes it to Redis. Other Thor apps subscribe to Redis channels to receive real-time updates.

**Key Principle:** LiveData is a "dumb pipe" - it just fetches and publishes data. Your business logic apps (FutureTrading, account_statement, etc.) decide what to do with it.

---

## Structure

```
LiveData/
  shared/                  # Shared Redis client used by all brokers
    redis_client.py        # live_data_redis singleton
    channels.py            # Channel naming conventions
  
  schwab/                  # Schwab OAuth + Trading API
    models.py              # SchwabToken (OAuth storage only)
    tokens.py              # OAuth helpers
    services.py            # API client (fetch positions/balances/orders)
    urls.py, views.py      # OAuth endpoints
  
  tos/                     # Thinkorswim real-time streaming
    services.py            # WebSocket streamer (publishes quotes)
    urls.py, views.py      # Stream control endpoints
```

---

## How It Works

### 1. Brokers Publish to Redis

**TOS publishes quotes:**
```python
from LiveData.shared.redis_client import live_data_redis

# TOS receives quote from WebSocket
live_data_redis.publish_quote("AAPL", {
    "bid": 175.50,
    "ask": 175.51,
    "last": 175.50,
    "volume": 1000000
})
```

**Schwab publishes positions:**
```python
from LiveData.shared.redis_client import live_data_redis

# Schwab API returns position data
live_data_redis.publish_position(account_id, {
    "symbol": "AAPL",
    "quantity": 100,
    "market_value": 17550.00
})
```

### 2. Your Apps Subscribe to Redis

**FutureTrading subscribes to quotes:**
```python
import redis

r = redis.Redis()
pubsub = r.pubsub()
pubsub.subscribe("live_data:quotes:AAPL")

for message in pubsub.listen():
    quote = json.loads(message['data'])
    # Update your UI, save to DB, etc.
```

**account_statement subscribes to positions:**
```python
pubsub.subscribe("live_data:positions:12345")

for message in pubsub.listen():
    position = json.loads(message['data'])
    Position.objects.update_or_create(...)
```

---

## Redis Channels

All channels follow this pattern: `live_data:<type>:<identifier>`

| Channel | Published By | Data |
|---------|--------------|------|
| `live_data:quotes:{symbol}` | TOS | Real-time quotes (bid/ask/last/volume) |
| `live_data:positions:{account_id}` | Schwab | Holdings (symbol, quantity, value) |
| `live_data:balances:{account_id}` | Schwab | Cash, buying power, account value |
| `live_data:orders:{account_id}` | Schwab | Order fills and status updates |
| `live_data:transactions:{account_id}` | Schwab | Buy/sell history |

---

## Database Models

**Only ONE model exists:** `SchwabToken`

```python
# LiveData/schwab/models.py
class SchwabToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField()
    access_expires_at = models.BigIntegerField()
```

**Why just one?** OAuth tokens must be saved. Everything else (quotes, positions, balances) comes from APIs in real-time and goes straight to Redis. Your business logic apps decide what to persist.

---

## Adding a New Broker

Want to add Interactive Brokers? Just create a new app:

```
LiveData/
  ibkr/                    # New broker!
    models.py              # IBKRToken (if OAuth needed)
    services.py            # IBKR API client
    urls.py, views.py
```

Update settings:
```python
INSTALLED_APPS = [
    "LiveData.schwab.apps.SchwabConfig",
    "LiveData.tos.apps.TosConfig",
    "LiveData.ibkr.apps.IBKRConfig",  # ← Add one line
]
```

Done. No refactoring needed.

---

## API Endpoints

### Schwab OAuth
- `POST /api/schwab/oauth/start/` - Start OAuth flow
- `GET /api/schwab/oauth/callback/` - OAuth callback (Schwab redirects here)
- `GET /api/schwab/accounts/` - List connected accounts
- `GET /api/schwab/accounts/{id}/positions/` - Fetch positions (publishes to Redis)
- `GET /api/schwab/accounts/{id}/balances/` - Fetch balances (publishes to Redis)

### TOS Streaming
- `GET /api/feed/tos/status/` - Check streamer status
- `POST /api/feed/tos/subscribe/` - Subscribe to a symbol
- `POST /api/feed/tos/unsubscribe/` - Unsubscribe from a symbol

---

## Migration from Old SchwabLiveData

### What Changed
| Old | New |
|-----|-----|
| ❌ `SchwabLiveData/` folder | ✅ `LiveData/` folder |
| ❌ `DataFeed` model (config) | ✅ Redis pub/sub (no config needed) |
| ❌ `ConsumerApp` model (routing) | ✅ Apps just subscribe to channels |
| ❌ `provider_factory.py` (complex) | ✅ Direct Redis publishing (simple) |

### What Stayed the Same
- App label: `label = "SchwabLiveData"` (keeps DB tables intact)
- Migration history: No data loss

---

## Why This Architecture?

✅ **Simple** - No routing config, no provider factory, just publish/subscribe  
✅ **Flexible** - Add brokers without touching existing code  
✅ **Scalable** - Redis handles millions of messages/second  
✅ **Testable** - Each broker app is isolated  
✅ **Clear** - One job per app (Schwab = OAuth/API, TOS = streaming)  

---

## Next Steps (TODO)

1. ✅ Structure created
2. ✅ Database migrated
3. ⏳ Implement Schwab OAuth flow (`LiveData/schwab/tokens.py`)
4. ⏳ Implement TOS WebSocket connection (`LiveData/tos/services.py`)
5. ⏳ Refactor `FutureTrading/views.py` to subscribe to Redis
6. ⏳ Add IBKR integration (when needed)

---

**Questions?** Check the code in `LiveData/shared/redis_client.py` for usage examples.
