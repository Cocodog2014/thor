📈 Schwab → LiveData → Redis → ActAndPos → UI

This shows exactly how real Schwab data moves through Thor.

I’ll give you two versions:

High-level conceptual flow (perfect for documentation)

Detailed technical flow (perfect for implementation + debugging)

✅ 1. High-Level Flow Diagram
               ┌─────────────────────────┐
               │  User Logs Into Schwab  │
               │ (OAuth: LMS + 2FA flow) │
               └─────────────┬───────────┘
                             │
                             ▼
           ┌──────────────────────────────────────────┐
           │ Thor Backend (LiveData.schwab OAuth)     │
           │ - Receives OAuth callback (code=...)     │
           │ - Exchanges code → access + refresh token│
           │ - Stores tokens in BrokerConnection(user)│
           └──────────────┬──────────────────────────┘
                          │
     ┌────────────────────┼──────────────────────┐
     ▼                    ▼                      ▼
Real-time Balances  Real-time Positions   Real-time Quotes (future)
(Schwab API)        (Schwab API)          (Schwab / Market Data)


         ┌──────────────────────────────────────────────────┐
         │ LiveData.schwab.services                         │
         │ - fetch_balances()                               │
         │ - fetch_positions()                              │
         │ - normalize data                                  │
         │ - update ActAndPos models                        │
         │ - publish to Redis                               │
         └───────────────────────┬──────────────────────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │   Redis (Live Bus)     │
                     │ live_data:positions:*  │
                     │ live_data:balances:*   │
                     └────────────┬──────────┘
                                  │
                                  ▼
         ┌──────────────────────────────────────────────────┐
         │ ActAndPos (Database Models)                      │
         │ - Account (net liq, cash, BP, equity)            │
         │ - Position (symbol, qty, avg, mark)              │
         │ - Updated automatically when Schwab changes      │
         └──────────────────────────┬───────────────────────┘
                                    │
                                    ▼
         ┌──────────────────────────────────────────────────┐
         │ Thor Frontend (React UI)                         │
         │ - Account Summary Panel                           │
         │ - Positions Table                                 │
         │ - Activity / Orders view                         │
         │ - Auto-refresh using Redis or API polling         │
         └──────────────────────────────────────────────────┘

✅ 2. Technical Flow Diagram (step-by-step)

This diagram shows the actual endpoints, classes, and functions used.

STEP 1 — OAuth Login
User → Thor UI → /api/schwab/oauth/start/
    ↓ redirect
Schwab LMS Login → 2FA → Consent
    ↓ callback
Thor Backend → /api/schwab/oauth/callback?code=...


In callback:

exchange_code_for_tokens()
↓
BrokerConnection(user).save()

STEP 2 — Fetch Schwab Balances + Positions

Triggered by:

user opening account dashboard

cron / scheduled job

manual refresh

GET /api/schwab/accounts/<id>/balances/
GET /api/schwab/accounts/<id>/positions/


These call:

SchwabTraderAPI.fetch_account_details()
    ↓
    REST call → https://api.schwabapi.com/trader/v1/accounts/<id>?fields=positions
    ↓
    JSON normalized

STEP 3 — Update ActAndPos Models
Balances → Account table

Ref: 

accounts

account.cash = Schwab.cashBalance
account.net_liq = Schwab.liquidationValue
account.equity = Schwab.equity
account.stock_buying_power = Schwab.stockBuyingPower
...
account.save()

Positions → Position table

Ref: 

positions

Position.update_or_create(
    account=Account,
    symbol=symbol,
    asset_type="EQ",
    defaults={
        quantity: long - short
        avg_price: Schwab.averagePrice
        mark_price: Schwab.marketValue / qty
    }
)

STEP 4 — Publish to Redis (Live Market Bus)

Ref: your Redis client: live_data_redis

live_data_redis.publish_balance(account_id, {
    cash,
    net_liq,
    buying_power,
    equity,
})

live_data_redis.publish_position(account_id, {
    symbol,
    qty,
    avg_price,
    market_value,
})


Redis Channels:

live_data:balances:{account_id}
live_data:positions:{account_id}

STEP 5 — UI Consumption (React)

The UI gets the live data via:

A. API polling (existing):
/api/actandpos/account_summary
/api/positions?account_id=...
/api/actandpos/activity/today

B. Or (future) live socket subscription:
subscribe("live_data:balances:<id>")
subscribe("live_data:positions:<id>")


UI updates:

Net Liq → Account Summary

Buying Power → Header

Positions Table

P/L Calculations

Activity / Order Tracking

✔ Final Summary Diagram (most compact)
Schwab → (OAuth) → BrokerConnection(user)
        → (API) → SchwabTraderAPI.fetch_*
                → normalize data
                → update ActAndPos.Account
                → update ActAndPos.Position
                → publish to Redis (live_data:*)
                → UI auto-updates via API / Redis


This is the correct & complete flow for your architecture.