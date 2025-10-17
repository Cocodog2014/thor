# LiveData Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      EXTERNAL DATA SOURCES                      │
├─────────────────────────────────────────────────────────────────┤
│  Schwab API          TOS WebSocket         IBKR Gateway         │
│  (REST)              (streaming)           (future)             │
└──────┬───────────────────┬──────────────────────┬───────────────┘
       │                   │                      │
       │                   │                      │
       ▼                   ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                       LIVEDATA/ PACKAGE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  schwab/               tos/                 ibkr/              │
│  ├── OAuth flow        ├── WebSocket        ├── (future)       │
│  ├── Fetch positions   ├── Stream quotes    └── ...            │
│  ├── Fetch balances    └── Publish          │
│  └── Place orders                           │
│                                                                 │
│  shared/                                                        │
│  ├── redis_client.py   ← All brokers use this                 │
│  └── channels.py       ← Channel naming                        │
└──────┬──────────────────────────────────────────────────────────┘
       │
       │ Publish to Redis
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                         REDIS PUB/SUB                           │
├─────────────────────────────────────────────────────────────────┤
│  Channels:                                                      │
│  • live_data:quotes:{symbol}                                   │
│  • live_data:positions:{account_id}                            │
│  • live_data:balances:{account_id}                             │
│  • live_data:orders:{account_id}                               │
│  • live_data:transactions:{account_id}                         │
└──────┬──────────────────────────────────────────────────────────┘
       │
       │ Subscribe
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR BUSINESS LOGIC APPS                     │
├─────────────────────────────────────────────────────────────────┤
│  FutureTrading/        account_statement/   thor-frontend/     │
│  ├── Subscribe         ├── Subscribe        ├── Subscribe      │
│  ├── Apply logic       ├── Save to DB       └── Display UI     │
│  └── Save signals      └── Generate reports                    │
└─────────────────────────────────────────────────────────────────┘
```

## Key Points

1. **LiveData apps = Publishers** (fetch data, publish to Redis)
2. **Business apps = Subscribers** (listen to Redis, apply logic)
3. **Redis = Message bus** (decouples data fetching from business logic)
4. **No direct dependencies** (FutureTrading doesn't import LiveData)

## Example Flow: Real-time Quote

```
TOS WebSocket
    ↓ receives quote for AAPL
LiveData.tos.services.TOSStreamer
    ↓ calls live_data_redis.publish_quote()
Redis Channel: live_data:quotes:AAPL
    ↓ broadcasts to all subscribers
FutureTrading app
    ↓ receives message
    ↓ enriches with signals
    ↓ saves to MarketData table
thor-frontend
    ↓ receives message
    ↓ updates UI in real-time
```

## Example Flow: Account Position

```
User clicks "Sync Positions"
    ↓ POST /api/schwab/accounts/12345/positions/
LiveData.schwab.services.SchwabTraderAPI
    ↓ fetches from Schwab API
    ↓ calls live_data_redis.publish_position()
Redis Channel: live_data:positions:12345
    ↓ broadcasts to subscribers
account_statement app
    ↓ receives message
    ↓ updates Position model
    ↓ triggers rebalancing check
```
