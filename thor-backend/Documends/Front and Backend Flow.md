Here is the clean, correct front-end ↔ back-end flow for your trading platform as of today, including what you already have, what needs to be added, and what you're missing.

### 2025-12-09 Front-End Updates (Home Command Experience)

- The home dashboard now launches a three-scene Commander Welcome modal (rendered from `CommanderWelcomeModal.tsx`) the first time a session loads. Dismissal state is persisted with the `thor.home.welcome.dismissed` sessionStorage key so returning users skip the sequence unless storage is cleared.
- Scene 1 (“Captain on deck” → “Workhorse Stable shield 100 percent”) displays for 6s with staged callouts; hover/fade timings are handled inside the modal component.
- Scene 2 shows “Engine room to Captain. Controls are yours.” for 4s once the Scene 1 → Scene 2 rotation completes. The Engage button is available only during Scene 2 and is disabled while the finale sequence is running.
- Tapping Engage transitions to Scene 3 (“Your war room is activated…”) with a 3s message overlay before the modal auto-dismisses and routing returns to `/app/home`.
- All three scenes use portal rendering, layered image animations, and timed callouts governed by React state hooks; CSS lives beside the component and includes rotate-in/out keyframes plus distinctive theming per scene.

### Production Runtime Stack (Thor Cloud Footprint)

- **Thor Web (Vite/React build served by Nginx/engineX container)** – static assets are built via `thor-frontend`, baked into the `thor-web` image, and fronted by the engineX reverse proxy. engineX terminates TLS, serves the SPA, and proxies API requests to the backend container network.
- **Thor Backend (Django + Gunicorn)** – packaged as `thor-backend` service. Gunicorn workers run the Django app, expose the REST API, WebSocket endpoints, and upload/download routes. Requests from engineX hit this service over the internal Docker network.
- **Thor Workers** – dedicated Celery/async worker container that shares the backend codebase but executes background jobs (paper engine fills, market data ingestion, scheduled account snaps). Pulled from the same image but launched with the worker entrypoint so long-running jobs don’t block the web tier.
- **Redis** – central message bus + cache. Used for:
        - Celery broker between Thor Web/Gunicorn and Thor Workers
        - LiveData pub/sub channels (quotes, fills, telemetry)
        - Short-lived session/cache data for dashboards
- **PostgreSQL** – authoritative datastore for users, accounts, orders, positions, telemetry snapshots. Runs in its own container with mounted volume (`docker/postgres/data`). All Django apps point to this instance via internal hostname `postgres`.
- **Networking** – docker compose wires all containers (engineX, thor-web, thor-backend, thor-workers, redis, postgres) onto the `thor_app_net`. Only engineX exposes ports to the host, so everything else stays private behind the proxy.
- **Deploy Flow** – `docker-compose up -d --build` rebuilds thor-frontend + thor-backend images, restarts engineX, migrates postgres, and resurrects workers so the full stack stays in sync.

✅ FULL SYSTEM FLOW — FRONT + BACK FOR TRADING

Customer Opens an Account
Backend

Already built in your Django backend (Users, Accounts models).

Each customer can have:

Paper Trading account

Real (Schwab) account (future)

Frontend

Registration and login working.

Nothing more to add here.

2. Customer Has Money in the Account
A. Paper Money

You want every new paper account to initialize with:
$100,000.00 starting balance

Required Implementation

Backend (Trades or ActAndPos):

When a paper account is created, set:

starting_balance = 100000.00
current_cash = 100000.00
equity = 100000.00


Frontend

Show the balance in the Banner (you already do).

This part is simple and ready to implement.

3. Customer Makes a Trade

This activates the core real-time trading flow, which must be smooth and correct.

Front End

User fills:

symbol (META, AAPL, etc.)

quantity

price (market/limit)

buy or sell

Sends POST → Trades API.

Backend: Trades App

When a trade request comes in:

Validate order

Check account cash

Create the Order record

Pass the order to the Paper Engine

Paper engine:

Creates/updates Position in ActAndPos

Reserves cash if needed (for open orders)

Executes instantly if market order

3A. Live Data Must Drive Everything in Real Time

This is the most important part you asked about.

Your real-time loop is:

ThinkOrSwim → Excel → LiveData app → Redis → ActAndPos / Trades / Frontend


For each active position:

LiveData provides:

last price

bid/ask

percent change

timestamp

Backend must do:

For each position:

real_time_value = quantity * last_price
profit_loss = (last_price - avg_price) * quantity
account_equity = cash + sum(position values)

These must update:

Every tick (Redis pub/sub)

Every 0.5–1 second on the front end

3B. Customer Must See P/L and Account Updating Live
What is required:
Backend

ActAndPos retrieves snapshot from LiveData

Computes P/L

Computes updated cash + equity

Emits websocket event or is polled by frontend

Frontend

Update UI values in:

Account Banner

Positions table

P/L cards

Every second or faster

3C. “Edit a Trade Before It Goes Through”

This is a missing feature — let’s define it clearly.

For paper trading you want:

When a customer submits an order:

Order enters Pending state

Customer can:

❌ Cancel order

✏️ Edit order

When the order is executed:

Becomes Filled

Customer can no longer edit it (only close by selling)

We need to add:

OrderStatus: PENDING, FILLED, CANCELLED

API endpoints:

PATCH /orders/<id>/update

POST /orders/<id>/cancel

Frontend:

Show pending orders

Show edit/cancel buttons

Show countdown (optional)

🚀 WHAT YOU ARE MISSING (THE GAPS)

Here is exactly what’s missing from the system you described:

1. Real-Time Account Engine

You need a backend process that constantly recalculates:

Unrealized P/L

Total account equity

Margin remaining

Cash changes

Position value

Leverage (future)

Right now this is partially implemented, but not fully automated.

2. Order States

Paper trading currently executes immediately.
We need Pending → Filled → Closed states.

3. Ability to Edit or Cancel Pending Orders

Not implemented yet.

4. Front-End Real-Time Subscription

The front end must subscribe to either:

Websocket feed
or

High-speed polling (every 1s)

To update:

Prices

P/L

Account balance

Position values

5. Position Event History

You also want:

“Worked” / “Didn’t Work” summary

Composite stats

This requires:

Logging at open

Logging at close

Tracking performance

✅ FINAL CHECKLIST FOR TODAY — WHAT WE SHOULD BUILD
Backend:

Paper account auto-starts with $100,000

Real-time P/L calculation loop

Real-time account equity updates

Pending → Filled order lifecycle

Edit or cancel pending orders

Endpoints for real-time snapshot

Frontend:

Live updating account banner

Live updating positions

Live total equity

UI to edit/cancel orders

Orders table with statuses

Text Version (matches diagram)
┌────────────────────────────┐
│      Customer Frontend     │
│  (React, TS, Thor UI)      │
│                            │
│  - Account dashboard       │
│  - Positions               │
│  - Orders & editing        │
│  - P/L & Equity live       │
└───────────────┬────────────┘
                │
                ▼
        HTTP / Websocket
                │
                ▼
┌──────────────────────────────────────────┐
│              Django Backend              │
├──────────────────────────────────────────┤
│  Auth / Accounts                         │
│  Trades API                               │
│  ActAndPos (positions, P/L engine)        │
│                                           │
│  1. Receive order from frontend           │
│  2. Validate cash                         │
│  3. Create order (PENDING)                │
│  4. Paper Engine decides fill             │
│  5. Update positions                      │
│  6. Emit real-time account snapshot       │
└───────────────────┬──────────────────────┘
                    │
                    ▼
             REST Call / Redis
                    │
                    ▼
┌──────────────────────────────────────────┐
│                 LiveData                 │
│  (TOS Excel → Reader → Redis → REST)     │
├──────────────────────────────────────────┤
│  - Reads real quotes from Excel/TOS      │
│  - Normalizes data                       │
│  - Publishes to Redis channels           │
│  - Provides /snapshot?symbols=… API      │
└───────────────────┬──────────────────────┘
                    │
                    ▼
          TOS / Schwab / Market Feeds


This diagram shows the full data flow from a customer's screen → LiveData → backend → frontend updates.

2️⃣ ORDER LIFECYCLE FLOW
Text Version (matches diagram)
CUSTOMER CLICKS "BUY"
        │
        ▼
┌────────────────────────────┐
│  Trades API (Create Order) │
└────────────────────────────┘
        │
        ▼
Order created with:
status = "PENDING"
reserved_cash = qty * price_estimate
        │
        ▼
┌────────────────────────────┐
│     Paper Execution Engine │
└────────────────────────────┘
        │
        ▼
Checks:
- Market open? (optional)
- Symbol live?
- Sufficient cash?
- Price reachable?
        │
        ▼
IF MARKET ORDER → fill immediately  
IF LIMIT ORDER → wait until price touches  
        │
        ▼
Order moves to → **FILLED**
Position updated or created
Cash adjusted
        │
        ▼
Backend broadcasts → FRONTEND
- New position
- New balance
- Real-time P/L begins


This gives your system clean order states:

PENDING

FILLED

CANCELLED

REJECTED

And allows customers to edit or cancel pending orders — the feature you want.

3️⃣ REAL-TIME P/L + ACCOUNT UPDATE FLOW
Text Version (matches diagram)
┌───────────────────────────────┐
│        LIVE MARKET DATA       │
│      (TOS → Excel → LiveData) │
└───────────────────┬───────────┘
                    ▼
           LiveData publishes
              last_price
              bid/ask
              timestamp
              change %
                    │
                    ▼
┌──────────────────────────────────┐
│  ActAndPos (Real-Time Engine)   │
├──────────────────────────────────┤
│ For each open position:         │
│                                 │
│ value = qty * last_price        │
│ pnl = (last_price - avg) * qty  │
│                                 │
│ account_equity = cash + sum     │
│                                │
│ Broadcast new snapshot → FE     │
└───────────────────────┬────────┘
                        ▼
           FRONTEND REFRESHES
- Account banner  
- Positions table  
- Total P/L  
- Equity meter  


This is exactly how your system should operate every time a tick comes in.

https://www.timeplus.com/post/data-pipeline-architecture?utm_source=chatgpt.com