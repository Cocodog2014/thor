1. Updated dev diagram (with Cloudflare + new folders)

# Thor Development Guide

Thor is a futures-focused trading and research platform built on:

- **Django** (REST API, data pipeline, ML, trading engine)
- **React + Vite + TypeScript** (trading UI)
- **PostgreSQL + Parquet + DuckDB** (storage & analytics)
- **Redis** (live quote bus)
- **Cloudflare Tunnel** (secure remote access to dev backend)

Its core goal:  
> Establish the complete data storage and ML infrastructure that supports **live trading**, **historical analysis**, and **backtesting**.

---

## 1. Project Layout

Thor lives under `A:\Thor`.

### 1.1 Backend (`thor-backend`)
`FutureTrading/views/MarketOpenCapture.py` implements the single-table market open snapshot. Recent refactor removed an obsolete `vwap` field that was still being passed into `MarketSession.objects.create()`; this silently caused per-future row creation failures (only the TOTAL row succeeded). The service has been updated and validated across all enabled markets.


```text
thor-backend/
├── .vscode/                 # Editor config (launch, tasks, settings)
├── __pycache__/             # Python bytecode (ignore)
├── account_statement/       # Account & statement domain models
├── api/                     # REST API endpoints (quotes, session, ML, etc.)
├── core/                    # Shared utilities, base models, helpers
├── data/                    # Local data helpers, fixtures, small artifacts
├── FutureTrading/           # Futures instruments, RTD models, weights, signals
├── GlobalMarkets/           # Global markets / indices views & models
├── LiveData/                # Live quote pipeline (Excel → Redis, etc.)
├── scripts/                 # Admin / dev / ops scripts
├── templates/               # Django templates (HTML)
├── thor_project/            # Django settings, URLs, WSGI/ASGI
├── thordata/                # Data & analytics utilities
├── users/                   # Auth & user management
└── manage.py

Backend port (dev): http://127.0.0.1:8000

1.2 Frontend (thor-frontend)

thor-frontend/
├── dist/                    # Vite build output
├── node_modules/            # NPM deps
├── public/                  # Static assets
└── src/
    ├── assets/              # Images, icons, static media
    ├── components/          # Reusable UI widgets
    ├── context/             # React context providers (session, auth, etc.)
    ├── hooks/               # Custom hooks (SSE, quotes, forms)
    ├── layouts/             # Layout components (shell, panels)
    ├── pages/
    │   ├── AccountStatement/
    │   ├── ActivityPositions/
    │   ├── FutureTrading/
    │   ├── GlobalMarkets/
    │   └── User/
    ├── services/            # API clients (Thor backend, Schwab, etc.)
    ├── styles/              # Global & module styles
    ├── types/               # Shared TypeScript types/interfaces
    ├── App.css
    ├── App.tsx
    ├── main.tsx
    ├── theme.ts
    └── vite-env.d.ts

Frontend port (dev): http://127.0.0.1:5173

2. High-Level Architecture

flowchart LR
  subgraph Client
    BROWSER["Browser (React UI)<br/>thor-frontend"]
  end

  subgraph Edge
    CF["Cloudflare DNS + Tunnel<br/>thor.360edu.org (dev)"]
  end

  subgraph Backend["Backend - thor-backend"]
    DJ["Django API<br/>LiveData / FutureTrading / etc."]
    REDIS["Redis<br/>Live Quote Bus"]
    PG["PostgreSQL<br/>Ticks + Metadata"]
    PARQ["Parquet Files<br/>/data/ticks, /data/bars"]

  subgraph ML["ML & Trading"]
    FEAT["Feature Store"]
    MODELS["ML Models<br/>(scikit-learn, etc.)"]
    TRADER["Trading Engine<br/>Paper + Live (future)"]
  end

  BROWSER -->|SSE + REST| DJ
  BROWSER -->|Dev only| CF --> DJ

  DJ <--> REDIS
  REDIS --> PG
  PG <--> PARQ
  PARQ <--> DUCK
  DUCK <--> FEAT
  FEAT <--> MODELS
  MODELS --> TRADER
  TRADER --> DJ

3. Data & ML Infrastructure
PostgreSQL is the primary database:

Primary app data: instruments, weights, signals, users, configs

Historical ticks: one row per tick (Excel and later Schwab)

ACID transactions: correct and safe trading operations

Relational queries: joins across instruments, signals, sessions

Backups & recovery: WAL, dumps, etc.

thor_pgdata holds persistent data.
Run Postgres (dev)

Preferred (docker compose):

```powershell
cd A:\Thor
docker compose up -d postgres
```

- Exposes Postgres on `localhost:5432` (expected everywhere else in this guide).
- Data volume/location is handled by `docker-compose.yml` (no extra flags needed).

Fallback manual container (use only if you cannot rely on docker compose):

```powershell
docker run --name thor_postgres `
  -e POSTGRES_DB=thor_db `
  -e POSTGRES_USER=thor_user `
  -e POSTGRES_PASSWORD=thor_password `
  -e PGDATA=/var/lib/postgresql/data/pgdata `
  -v thor_pgdata:/var/lib/postgresql/data `
  -p 5433:5432 `
  -d postgres:13
```

Port 5433 in the fallback snippet avoids conflicts with an existing local Postgres install.

`thor_pgdata` holds persistent data for the manual container.

Core Tick Table

CREATE TABLE ticks (
    symbol     TEXT        NOT NULL,
    ts         TIMESTAMPTZ NOT NULL,
    last       NUMERIC,
    bid        NUMERIC,
    ask        NUMERIC,
    lastSize   INTEGER,
    bidSize    INTEGER,
    askSize    INTEGER,
    source     TEXT        NOT NULL,  -- EXCEL, SCHWAB, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ticks_symbol_ts ON ticks (symbol, ts);
CREATE INDEX idx_ticks_ts        ON ticks (ts);

Goal: every live quote you see in the UI should have a matching tick row here.

3.2 Redis – Live Quote Bus

Redis acts as the real-time hub:

Feeds live quotes to Django APIs and the React UI.

Buffers ticks before durable storage in PostgreSQL.

Powers SSE streaming and latency / source indicators.

Key patterns:

quotes:latest:<symbol> (HASH)
Latest snapshot per symbol (last, bid, ask, sizes, ts, source).

quotes:stream:unified (STREAM)
Canonical tick events used by:

Django SSE endpoint (/api/quotes/stream)

Redis→Postgres ingestor worker

Current live source: Excel RTD → Excel collector → Redis
(Schwab → Redis collector will join later.)

3.3 Parquet + DuckDB – Analytics & ML Storage

Once ticks are in PostgreSQL:

1. Export to Parquet (daily or by range)

2. Query with DuckDB for:

  OHLCV bar generation (1s, 1m, 5m, 1h, etc.)

  Feature engineering

  Backtesting

File layout (planned):

data/
└── ticks/
    ├── date=YYYY-MM-DD/
    │   ├── symbol=ES/ticks.parquet
    │   ├── symbol=YM/ticks.parquet
    │   └── symbol=NQ/ticks.parquet
└── bars/
    └── date=YYYY-MM-DD/
        └── symbol=ES/bars_1m.parquet

Example DuckDB query:

import duckdb

con = duckdb.connect()
df = con.execute("""
    SELECT symbol,
           date_trunc('minute', ts) AS minute,
           first(last) AS open,
           max(last)   AS high,
           min(last)   AS low,
           last(last)  AS close
    FROM read_parquet('data/ticks/date=2025-10-09/symbol=ES/*.parquet')
    GROUP BY symbol, minute
    ORDER BY minute
""").fetchdf()

4. Live Data Pipeline
4.1 Actual Current State

flowchart LR
  EXCEL["Excel RTD<br/>RTD_TOS.xlsm"] --> COL["Excel Collector<br/>poll_tos_excel"]
  COL --> RSTREAM["Redis Stream<br/>quotes:stream:unified"]
  COL --> RLATEST["Redis Hashes<br/>quotes:latest:<symbol>"]
  RSTREAM --> DJ["Django (LiveData)"]
  RLATEST --> DJ
  DJ --> UI["React UI<br/>FutureTrading page"]

✅ Running now

    Excel RTD integration

    Excel→Redis collector

    Redis latest + stream

    Django /api/quotes and /api/quotes/stream

    React SSE subscription and live table/heatmap

  Collector command: `python manage.py poll_tos_excel` against `RTD_TOS.xlsm` → `LiveData!A1:N13`.

❌ Not yet

    Redis→Postgres tick ingestor

    Tick → Parquet export

    Bar generation

    ML training & predictions on tick data

4.2 Intended Full Pipeline

flowchart LR
  subgraph Sources
    EXCEL["Excel RTD"]
    SCHWAB["Schwab API (future)"]
  end

  EXCEL --> REDIS_COL["Excel→Redis Collector"]
  SCHWAB --> SCHWAB_COL["Schwab→Redis Collector (future)"]

  REDIS_COL --> RSTREAM["Redis Stream\nquotes:stream:unified"]
  SCHWAB_COL --> RSTREAM
  REDIS_COL --> RLATEST["Redis Latest\nquotes:latest:<symbol>"]
  SCHWAB_COL --> RLATEST

  RSTREAM --> INGEST["Redis→Postgres Ingestor"]
  INGEST --> PG["PostgreSQL ticks"]
  PG --> EXPORT["Export to Parquet"]
  EXPORT --> PARQ["Parquet"]
  PARQ --> DUCK["DuckDB / Polars"]
  DUCK --> FEAT["Feature Store"]
  FEAT --> ML["ML Models"]
  ML --> TRADER["Trading Engine"]
  TRADER --> PG

The keystone that unlocks everything else is the Redis→Postgres ingestor.

5. ML Pipeline
5.1 ML Architecture

flowchart TB
  PARQ["Parquet Ticks + Bars"] --> DUCK["DuckDB / Polars Loader"]
  DUCK --> FEATS["Feature Engineering\n(technical, stats, cross-asset, session)"]
  FEATS --> FSTORE["Feature Store\n(Postgres + Parquet mirror + Redis cache)"]

  subgraph Offline Training
    FSTORE --> TRAIN["Model Training\n(scikit-learn, walk-forward)"]
    TRAIN --> REG["Model Registry\n(MLflow + Django)"]
  end

  subgraph Online Inference
    RLATEST["Redis Latest Quotes"] --> LIVE_FEATS["Live Feature Builder"]
    LIVE_FEATS --> INFER["Model Inference\n(in-memory models)"]
    REG --> INFER
    INFER --> SIGNALS["Signals\n(direction, magnitude, volatility, confidence)"]
  end

5.2 What Models Predict

Direction: Up / down over horizon (classification)

Magnitude: Expected return over horizon (regression)

Volatility: Risk estimate (for sizing)

Horizons:

Very short: 1–5 minutes

Short: 15–60 minutes

Daily / session-level for regime detection

5.3 Feature Categories

Price stats: returns, log returns, rolling mean/std, drawdown

Technical: MA/EMA, RSI, MACD, Bollinger, ATR, ADX, etc.

Microstructure (later): spread, order imbalance, tick direction

Cross-asset: ES/YM/NQ/RTY correlations and relative strength

Session context: time of day, session number, pre/post market

Volatility regime: realized and forecasted volatility

6. Trading Engine (Design)
6.1 Flow

flowchart LR
  SIGNAL["ML Signal\n(side, horizon, confidence, target, stop)"]
  SIGNAL --> RISK["Risk Engine\n(limits, exposure, daily loss)"]
  RISK -->|OK| SIZE["Position Sizer\n(Kelly + vol scaling)"]
  RISK -->|Reject| LOGR["Log / Reject\n(no order)"]

  SIZE --> ORDER["Order Builder\n(symbol, qty, type, limits/stops)"]
  ORDER --> ADAPT["Broker Adapter Layer"]

  subgraph Brokers
    PAPER["PaperTradingBroker"]
    SCHWAB["SchwabBroker (future)"]
  end

  ADAPT --> PAPER
  ADAPT --> SCHWAB

  PAPER --> POS["Positions / P&L"]
  SCHWAB --> POS
  POS --> FEEDBACK["Labeling & Model Feedback"]

6.2 Responsibilities

Risk engine

    Max contracts per symbol

    Max portfolio exposure

    Daily loss limits & circuit breakers

    Session awareness (don’t open new positions into the close)

Position sizing

    Use ML win probability and payoff ratio

    Compute capped Kelly fraction

    Convert risk budget → contracts using ATR or vol

    Enforce symbol & portfolio caps

Broker adapters

    PaperTradingBroker: local simulation (latency + slippage)

    SchwabBroker: real execution using Schwab API (later)

Feedback loop

    Every trade logs features + predictions + outcomes

    Used for model evaluation and retraining

7. Monitoring & Observability (Concept)

flowchart TB
  subgraph Runtime
    DJ["Django + Collectors + Ingestors + Trading"]
  end

  DJ --> METRICS["Prometheus Metrics Exporter"]
  DJ --> LOGS["Structured Logs"]

  METRICS --> GRAF["Grafana Dashboards"]
  METRICS --> ALERTM["Alertmanager"]

  ALERTM --> SLACK["Slack / Teams"]
  ALERTM --> PAGER["PagerDuty / SMS"]

  LOGS --> VIEW["Log Viewer / ELK (optional)"]

Typical SLOs (targets):

    P95 SSE latency < 300 ms

    Redis → Postgres lag < 2 s

    Parquet export done < 5 min after market close

8. Cloudflare Tunnel (Dev Only – Important)

Cloudflare Tunnel exposes both Django (`:8000`) and Vite (`:5173`) so remote browsers and Schwab OAuth can reach your dev box over HTTPS.

- Hostname: `https://thor.360edu.org`
- Used for: Schwab OAuth start/callback, remote admin/API access, UI demos

8.1 Concept Diagram

flowchart LR
  BROWSER["Your browser\n(https://thor.360edu.org)"] --> CF["Cloudflare DNS + Tunnel"]
  CF --> CLOUDFL["cloudflared agent\n(running on dev machine)"]
  CLOUDFL --> DJANGO["Django dev server\nhttp://127.0.0.1:8000"]
  CLOUDFL --> VITE["Vite preview\nhttp://127.0.0.1:5173"]

8.2 Key Dev Facts

- Tunnel name: `thor`
- Config file: `%USERPROFILE%\.cloudflared\config.yml`
- Credentials: `%USERPROFILE%\.cloudflared\<TUNNEL-UUID>.json`

Sample mapping:

```yaml
tunnel: thor
credentials-file: C:\Users\<you>\.cloudflared\<TUNNEL-UUID>.json


  - hostname: thor.360edu.org
    service: http://127.0.0.1:5173
  - hostname: thor.360edu.org
    path: /admin*
    service: http://127.0.0.1:8000
  - hostname: thor.360edu.org
    path: /api*
    service: http://127.0.0.1:8000
  - hostname: thor.360edu.org
    path: /static*
    service: http://127.0.0.1:8000
  - hostname: thor.360edu.org
    path: /media*
    service: http://127.0.0.1:8000
  - service: http_status:404
```

Schwab dev endpoints:

- OAuth start: `https://thor.360edu.org/api/schwab/oauth/start/`
- OAuth callback: `https://thor.360edu.org/schwab/callback`

Keep this dev-only and only run the tunnel when you actually need it.
9. Current Status vs To-Do
9.1 What’s Working Today

    ✅ Django backend running (thor-backend)

    ✅ React + Vite frontend running (thor-frontend)

    ✅ Redis running (Docker)

    ✅ Excel RTD → Redis collector

    ✅ /api/quotes and /api/quotes/stream endpoints

    ✅ React FutureTrading page reading live quotes

    ✅ Market session API (timezone app) for open/closed state

    ✅ Cloudflare Tunnel plan validated (not always running)

9.2 Critical Path To-Do (in order)

    Redis → PostgreSQL tick ingestor

    Consume quotes:stream:unified

    Write into ticks with batching

    Handle duplicates & errors safely

Postgres → Parquet export

    Daily command: export_to_parquet --date=YYYY-MM-DD

    Partition by date= and symbol=

Bar generation

    Use DuckDB to build 1s/1m/5m/1h bars

    Store into data/bars

Basic ML pipeline

    Load Parquet → DuckDB → Polars

    Build features for a few core symbols (ES, YM, NQ)

    Train simple baseline models (direction + volatility)

Paper trading engine

    Order model + position model

    Risk checks + simple sizing

    PaperTradingBroker hooked to live ticks

Schwab → Redis collector (optional after paper)

    Same canonical tick schema

    Dual source: EXCEL + SCHWAB

Monitoring hardening

    Prometheus metrics endpoint

    Simple Grafana dashboards

    Alerts for: no ticks during market, high lag, etc.

10. Quick Dev Workflow

1. Start databases & cache

```powershell
cd A:\Thor
docker compose up -d postgres
docker compose up -d redis
```

2. Run backend (new shell)

```powershell
cd A:\Thor\thor-backend
# conda activate Thor_inv       # if applicable
$env:DATA_PROVIDER    = 'excel_live'
$env:EXCEL_DATA_FILE  = 'A:\\Thor\\RTD_TOS.xlsm'
$env:EXCEL_SHEET_NAME = 'LiveData'
$env:EXCEL_LIVE_RANGE = 'A1:N13'
$env:REDIS_URL        = 'redis://localhost:6379/0'
# optional: disable background 52-week monitor
# $env:FUTURETRADING_ENABLE_52W_MONITOR = '0'
python manage.py runserver
```

3. Run frontend (new shell)

```powershell
cd A:\Thor\thor-frontend
npm install       # first time only
npm run dev       # http://localhost:5173
```

4. Start Excel → Redis poller (new shell)

```powershell
cd A:\Thor\thor-backend
python manage.py poll_tos_excel
```

5. (Optional) Run Cloudflare Tunnel (dev)

```powershell
cd A:\Thor
cloudflared tunnel run thor
```


6. (Optional) Start Market Open Grader (new shell)

The grader monitors pending MarketSession rows and updates their `wndw` field based on live prices hitting targets.

```powershell
cd A:\Thor\thor-backend

# Start with default 0.5s check interval
python manage.py start_market_grader

# Or customize interval
python manage.py start_market_grader --interval 1.0
```

What it does:
- Watches all `MarketSession` rows with `wndw='PENDING'`
- Reads live bid/ask from Redis
- Compares current price against `target_high` and `target_low`
- Updates `wndw` to `WORKED`, `DIDNT_WORK`, or `NEUTRAL`
- Runs continuously (stop with Ctrl+C)

Logic:
- **BUY/STRONG_BUY**: price >= target_high  WORKED; price <= target_low  DIDNT_WORK
- **SELL/STRONG_SELL**: price <= target_low  WORKED; price >= target_high  DIDNT_WORK
- **HOLD** or missing targets  NEUTRAL (no grading)

7. Futures Capture Control (Canada/Mexico Skip Logic)

Thor now supports per-market control over whether futures "open" snapshots are written into `FutureTrading.MarketSession`.

Use cases:
  - Suppress redundant markets (e.g., Canada, Mexico) whose futures mirror USA session.
  - Temporarily disable capture for maintenance/testing without code changes.

### 7.1 Model Flags

`GlobalMarkets.Market` has three Boolean fields exposed in the Django admin:

| Field | Purpose |
|-------|---------|
| `enable_futures_capture` | Master switch. If false, no MarketSession rows are written for this market. |
| `enable_open_capture` | Controls open-event capture (market transitions to OPEN). |
| `enable_close_capture` | Reserved for future close-event snapshots (not yet implemented). |

For Canada/Mexico: uncheck `enable_futures_capture` (and optionally `enable_open_capture`) to skip their rows completely.

### 7.2 How It Works Internally

1. `GlobalMarkets.monitor.MarketMonitor` drives exact open/close transitions by updating `Market.status` using timers.
2. After a market transitions to `OPEN`, `_on_market_open(market)` is invoked.
3. `_on_market_open` performs belt-and-suspenders checks:
   - `if not market.enable_futures_capture: return`
   - `if not market.enable_open_capture: return`
4. If allowed, it lazily imports `capture_market_open` from `FutureTrading.views.MarketOpenCapture`.
5. `capture_market_open` creates 12 `MarketSession` rows (11 individual futures + TOTAL) with a unified `session_number`.
6. Additional internal checks inside `MarketOpenCaptureService` also guard the flags (defensive redundancy).

This dual-layer (monitor + service) approach ensures:
  - Safe operation during migrations (service falls back to `getattr(..., True)` if flags absent).
  - No accidental writes if the monitor logic changes later.

### 7.3 Admin Workflow

1. Visit `/admin/GlobalMarkets/market/`.
2. Locate Canada and Mexico.
3. Uncheck `Enable futures capture` (and optionally `Enable open capture`).
4. Save.
5. Restart the backend (or wait for next OPEN transition) to see skips logged.

Expected log lines:

```
INFO Skipping futures open capture for Canada (enable_futures_capture=False)
INFO Skipping futures open capture for Mexico (enable_futures_capture=False)
```

Enabled markets will show:

```
INFO 🚀 Initiating futures open capture for USA
INFO Capture complete: Session #42, 12 rows created
```

### 7.4 Environment Guard

During migrations you may want to prevent the monitor from starting and querying tables before new columns exist. Set:

```powershell
$env:DISABLE_GLOBAL_MARKETS_MONITOR = '1'
python manage.py makemigrations
python manage.py migrate
```

Then unset or restart without the variable to resume normal scheduling.

### 7.5 Verification Checklist

After enabling/disabling flags:

| Step | Check |
|------|-------|
| Open transition fires | Log shows status change `CLOSED → OPEN` |
| Capture skip (disabled) | Skip message appears, no new `MarketSession` rows for that country |
| Capture success (enabled) | 12 rows inserted with identical `session_number` |
| TOTAL row present | One row where `future='TOTAL'` |
| Targets assigned | Rows with composite BUY/SELL have `entry_price`, `target_high`, `target_low` |

### 7.6 Future Extension

`enable_close_capture` is reserved; adding a symmetric `_on_market_close` hook will allow end-of-session snapshots (e.g., realized range vs targets). That code path intentionally omitted for now per project priority.

### 7.7 Market Open Capture: Session Number vs Date Fields

The Market Open snapshot (12 rows: 11 futures + TOTAL) is keyed by a monotonic `session_number` rather than the trio of `year`/`month`/`date` integers when grouping or validating a capture event.

Why `session_number` is authoritative:
- Timezone Safety: Markets (e.g., Japan, China) open on a local calendar day that can differ from the server's date rollover window. Relying on naive `date` comparisons produced false negatives in validation scripts.
- Atomicity: All 12 rows are created inside one logical capture transaction; they share exactly the same `session_number`, even if the open straddles midnight UTC boundaries.
- Sequential Integrity: `session_number` is incremented once per successful open capture per country, creating a simple ordered history without gaps (unless a market was disabled).

Date Fields Still Stored:
- Each `MarketSession` row still records `year`, `month`, `date` for human-readable audit and UI display.
- These fields should NOT be used as the primary grouping key for programmatic verification, reconciliation, or backfills.

Recommended Query Patterns:
```sql
-- Latest complete open snapshot for USA
SELECT * FROM future_trading_marketsession
WHERE country = 'USA' AND session_number = (
  SELECT MAX(session_number) FROM future_trading_marketsession WHERE country = 'USA'
);

-- Validate row count (expect 12)
SELECT COUNT(*) FROM future_trading_marketsession
WHERE country = 'USA' AND session_number = 42;  -- replace 42 with discovered latest

-- Fetch TOTAL composite row only
SELECT * FROM future_trading_marketsession
WHERE country = 'USA' AND session_number = 42 AND future = 'TOTAL';
```

Verification Scripts:
- `TestScript/test_capture_fix.py` (single-market) and `TestScript/verify_all_market_open_capture.py` (multi-market) have been updated to pivot on `session_number`.
- If a market is disabled (`enable_futures_capture=False`), its `session_number` will not increment—scripts skip those countries to avoid noise.

Legacy Field Note:
- The deprecated `vwap` column was removed from `MarketSession` and must not be passed during row creation. Attempting to include it caused silent drop of per-future rows prior to this fix.

Operational Guidance:
- When diagnosing a suspected missing future row, first capture the latest `session_number`; never infer grouping by matching on today's `date`.
- For backfill or data repair, operate in ascending `session_number` order to preserve chronological logic across timezone boundaries.

In short: treat `session_number` as the single source of truth for an open snapshot; treat `date` as metadata.

---

## 8. Thor Background Stack (`stack_start.py`)

Thor now centralizes all long-running futures workers inside `FutureTrading/services/stack_start.py`. The module exposes `start_thor_background_stack()`, which is responsible for starting every background supervisor that must run beside Django.

### 8.1 Responsibilities
- Launches the Excel → Redis poller, Market Open Grader, and Market Open Capture supervisor via dedicated daemon threads.
- Ensures the threads auto-restart if any worker crashes, so the dev server does not have to be restarted manually.
- Keeps the legacy 52-week and Pre-open supervisors separate but still initiated from the same AppConfig boot sequence, so all background activity is logged together.

### 8.2 Startup Flow
1. `FutureTrading/apps.py` calls `start_thor_background_stack()` from `FuturetradingConfig.ready()` using a short delayed thread (`ThorStackDelayedStart`).
2. The delayed call avoids database access during Django bootstrap and plays nicely with the autoreloader.
3. Once the guard checks (below) pass, `stack_start.py` spawns daemon threads for each supervisor and immediately returns control to Django. `runserver` or gunicorn can finish starting while the workers run in the background.

### 8.3 Safety Guards
`start_thor_background_stack()` exits early when:
- The current command is a management utility (`migrate`, `shell`, `test`, etc.).
- The process is not the main autoreload worker (`os.environ.get("RUN_MAIN") != "true"`).
- The stack has already been started once in this PID (idempotent flag stored inside the module).

These checks prevent double-starts and ensure database migrations or tests are not polluted by long-running threads.

### 8.4 Extending the Stack
- Add new supervisors inside `FutureTrading/services/stack_start.py` so they inherit the same safety guarantees.
- Keep each supervisor self-contained (start/stop helpers, logging) but register it through the central stack to avoid duplicate orchestration logic sprinkled throughout the codebase.
- If a supervisor needs configuration flags (intervals, enable/disable), read environment variables within that supervisor, not in `apps.py`.

### 8.5 Verifying Startup
- Watch the Django console for the log lines emitted by `FuturetradingConfig.ready()`:
  - `🔥 FutureTrading app ready: initializing background stack (delayed)...`
  - `🚀 Thor master stack started successfully.`
- Each worker also logs its own heartbeat; absence of those logs usually means one of the guard clauses short-circuited (e.g., running `manage.py shell`).

If you need to disable the stack temporarily, set an environment flag leveraged inside `stack_start.py` (see comments in that file) or comment out the call in `apps.py` while debugging.

## 9. Intraday Market Supervisor

The **IntradayMarketSupervisor** is an automated background service that manages real-time metric updates for each open market. It runs continuously during market hours and handles market-specific high/low/close/range calculations.

### 9.1 What It Does

The supervisor maintains separate worker threads for each open market and:

- **During market hours (OPEN)**:
  - Updates `MarketHighMetric` every 10 seconds (default)
  - Updates `MarketLowMetric` every 10 seconds (default)
  - Tracks intraday high/low values for all 11 futures symbols

- **On market close**:
  - Stops the intraday worker thread
  - Executes `MarketCloseMetric.update_for_country_on_close()`
  - Executes `MarketRangeMetric.update_for_country_on_close()`
  - Captures final session statistics

### 9.2 Architecture

```
MarketMonitor (GlobalMarkets)
    ↓
Market.status → OPEN
    ↓
Signal: _on_market_open(market)
    ↓
IntradayMarketSupervisor.on_market_open(market)
    ↓
Spawns worker thread for that market
    ↓
Worker polls every 10s (configurable)
    ↓
Calls MarketHighMetric.update_from_quotes()
    ↓
Calls MarketLowMetric.update_from_quotes()
    ↓
Market.status → CLOSED
    ↓
IntradayMarketSupervisor.on_market_close(market)
    ↓
Stops worker thread
    ↓
Calls MarketCloseMetric + MarketRangeMetric
```

### 9.3 Automatic Startup

The supervisor starts **automatically** when Django starts via the `FutureTrading` app configuration:

**File**: `FutureTrading/apps.py`
```python
class FuturetradingConfig(AppConfig):
    def ready(self):
        # ... other initialization ...
        from GlobalMarkets.monitor import start_monitor
        start_monitor()  # ← Starts MarketMonitor which manages IntradayMarketSupervisor
```

When a market transitions to OPEN:
1. `MarketMonitor` updates `Market.status = 'OPEN'`
2. `_on_market_open(market)` is called
3. `IntradayMarketSupervisor.on_market_open(market)` spawns a worker thread
4. Worker runs until market closes

### 9.4 Worker Thread Behavior

Each market gets its own daemon thread named `Intraday-{country}`:

```python
# Inside IntradayMarketSupervisor._worker_loop
while not stop_event.is_set():
    enriched, composite = get_enriched_quotes_with_composite()
    MarketHighMetric.update_from_quotes(country, enriched)
    MarketLowMetric.update_from_quotes(country, enriched)
    time.sleep(10)  # Default interval
```

The thread is **daemon=True**, meaning it won't prevent Django shutdown.

### 9.5 Manual Control

**Check if running**:
```powershell
# Django must be running for supervisor to work
python manage.py runserver
```

**Monitor market status manually**:
```powershell
# One-time check
python manage.py monitor_markets --once

# Continuous monitoring (alternative to automatic)
python manage.py monitor_markets --interval 60
```

**Configuration**:
```python
# Default interval: 10 seconds
# To customize, modify in FutureTrading/services/IntradayMarketSupervisor.py:
intraday_market_supervisor = IntradayMarketSupervisor(interval_seconds=10)
```

### 9.6 Logging

The supervisor emits detailed logs:

```
INFO Intraday metrics worker STARTED for Japan
INFO ⏱️ Scheduled Japan next open in 3600s (at 2025-11-23T09:00:00+09:00)
INFO Intraday worker loop started for Japan
INFO 🔄 Japan: CLOSED → OPEN
INFO Intraday metrics worker STOPPED for Japan
INFO Intraday worker loop EXITING for Japan
```

**Log levels**:
- `INFO`: Normal operations (start/stop/schedule)
- `ERROR`: Failed metric updates or worker crashes
- `EXCEPTION`: Full stack traces for debugging

### 9.7 Integration Points

| Component | Purpose |
|-----------|---------|
| `MarketMonitor` | Triggers on_market_open/on_market_close |
| `get_enriched_quotes_with_composite()` | Fetches live quotes from Redis |
| `MarketHighMetric` | Tracks intraday highs per symbol |
| `MarketLowMetric` | Tracks intraday lows per symbol |
| `MarketCloseMetric` | Captures closing prices |
| `MarketRangeMetric` | Calculates session range |

### 9.8 Testing

Run unit tests:
```powershell
cd A:\Thor\thor-backend
python manage.py test FutureTrading.tests.test_intraday_supervisor
```

Test coverage includes:
- Worker thread lifecycle (start/stop)
- Metric updates during market hours
- Close metrics execution
- Multiple concurrent markets
- Error handling and recovery

### 9.9 Troubleshooting

**Supervisor not starting**:
- Check Django logs for `Market Scheduler started` message
- Verify `Market.is_control_market=True` for monitored markets
- Ensure `Market.is_active=True`

**Metrics not updating**:
- Check Redis has live quote data: `redis-cli HGETALL quotes:latest:YM`
- Verify worker thread is running in logs
- Check for exception traces in Django logs

**High CPU usage**:
- Default 10-second interval should be fine
- Increase `interval_seconds` if needed
- Check for database connection leaks

**Worker stuck after market close**:
- Worker threads are daemon threads and should exit cleanly
- Check for infinite loops in metric update code
- Restart Django to force cleanup

### 9.10 Future Enhancements

Planned improvements:
- [ ] Configurable intervals per market via database settings
- [ ] Metric update batching for efficiency
- [ ] WebSocket integration for real-time UI updates
- [ ] Historical metric replay for backtesting
- [ ] Health check endpoint for monitoring worker status

### 9.11 Intraday High / Low Metrics – Formulas & Behavior

Thor maintains two continuously updating intraday extrema metrics per `(country, future)` while a market is OPEN:

| Field | Meaning | Update Condition | Percentage Formula |
|-------|---------|------------------|--------------------|
| `market_high_open` | Highest `last_price` seen so far in the current session | New tick above prior high | — (stores raw price) |
| `market_high_pct_open` | Percent move from market open up to the intraday high | New tick above the stored high | `(high - open) / open * 100` |
| `market_low_open` | Lowest `last_price` seen so far in the current session | New tick below prior low | — (stores raw price) |
| `market_low_pct_open` | Percent run-up from current intraday low | Tick above the stored low | `(last_price - low) / low * 100` |

Key characteristics:
- `market_high_pct_open` is `0.0000` at the open and updates ONLY when a new higher high is set (it represents peak move versus the open price; it does **not** fall back when price retraces).
- `market_low_pct_open` is `0.0000` at the open and updates when price trades above the recorded low (run-up from the trough).
- Percentages are quantized to FOUR decimal places in the update functions and stored with `decimal_places=4` (migration `0062_alter_percentage_precision`).
- If `market_open` is not yet set or `last_price` is missing, the metric update for that future is skipped defensively.

Zero percentage diagnostics:
- High stays `0.0000`: market has not printed a value above the open yet.
- Low stays `0.0000`: price has not traded above the recorded low, or successive lower lows keep resetting run-up to zero.

Supervisor integration changes (recent):
- `IntradayMarketSupervisor` now starts immediately for markets that are already OPEN after the initial monitor reconciliation. This fixes the earlier issue where percentages stayed at zero because no worker thread was running mid-session.
- Diagnostic debug logs (`[DIAG High]`, `[DIAG Low]`) were temporarily added in `FutureTrading/services/market_metrics.py` to trace skip reasons and formula application; remove or downgrade once stable.

Precision change summary:
- Previous schema stored percentages with `decimal_places=6`; now `decimal_places=4` for: `market_high_pct_open`, `market_low_pct_open`, `market_high_pct_close`, `market_low_pct_close`, `market_range_pct`, `range_percent`, `range_pct_52w`.
- Runtime quantization enforces four decimals BEFORE saving to avoid unnecessary rounding drift.

Operational guidance:
1. Confirm worker thread active via logs: `Intraday metrics worker STARTED for <country>`.
2. Sample a session row after a few ticks: values should show non-zero percentages once price moves off extremes.
3. Remove diagnostics: delete added debug lines or set logger level to INFO in production.

Example progression (high side):
```
Tick1 last=6719.50 → market_high_open=6719.50, market_high_pct_open=0.0000
Tick2 last=6719.25 → no new high, percent stays 0.0000 (still equal to open)
Tick3 last=6720.00 → NEW HIGH: market_high_open=6720.00, market_high_pct_open=(6720.00-6719.50)/6719.50*100=0.0074
``` 

Example progression (low side):
```
Tick1 last=6719.50 → market_low_open=6719.50, market_low_pct_open=0.0000
Tick2 last=6719.75 → runup=(6719.75-6719.50)=0.25; pct=0.25/6719.50*100=0.0037
Tick3 last=6719.10 → NEW LOWER LOW resets: market_low_open=6719.10, market_low_pct_open=0.0000
```

Planned future adjustments:
- Optional smoothing/EMA on drawdown/run-up for volatility-aware UI.
- Threshold-based alerting for large intraday reversals.
- Export of intraday high/low trajectory for ML feature engineering.

### 9.12 Manual Market Close Capture

Under normal operation the intraday worker triggers close and range metrics automatically when a market transitions to `CLOSED`. A manual API hook exists for reconciliation or forced re-run:

Endpoint:
```
GET /api/future-trading/market-close/capture?country=United%20States
GET /api/future-trading/market-close/capture?country=United%20States&force=1  # recompute even if already closed
```

Behavior:
1. Locates latest `session_number` for the country.
2. Skips if `market_close` already populated (unless `force=1`).
3. Fetches a fresh enriched quote snapshot.
4. Runs:
  - `MarketCloseMetric.update_for_country_on_close(country, enriched)`
  - `MarketRangeMetric.update_for_country_on_close(country)`
5. Returns JSON summary `{ status, session_number, close_rows_updated, range_rows_updated }`.

Use Cases:
- Recover from worker outage or missed CLOSE event.
- Recalculate after correcting a bad tick (use `force=1`).
- Operational monitoring / dashboard button.

Idempotency:
- Without `force=1` the view will not overwrite existing close metrics.
- With `force=1` values are recomputed using the current enriched prices (ensure snapshot integrity first).

File Reference:
`FutureTrading/views/MarketCloseCapture.py`

Security / Access:
- Treat as admin-only or protect via auth layer if exposed publicly; recomputation can alter historical end-of-session values.

Future Enhancements:
- Batch close capture for all markets simultaneously.
- Include validation of expected session duration before permitting recompute.
- Add audit log row recording recomputation event & diff of changed values.

---

## 10. 52-Week High/Low Monitor

The **52-Week Monitor** automatically tracks and updates 52-week high/low extremes for all 11 futures symbols based on incoming live prices from Redis.

### 10.1 What It Does

- **Continuous monitoring**: Polls Redis every 1 second (default) for latest LAST prices
- **Automatic updates**: Updates database when new 52-week highs or lows occur
- **Market-aware operation**: Only runs when at least one global control market is OPEN
- **Symbol mapping**: Handles TOS RTD naming differences (RT↔RTY, 30YRBOND↔ZB)
- **API integration**: Injects 52w data into `/api/quotes/latest` for frontend display

### 10.2 Architecture

```
Week52ExtremesSupervisor (checks every 60s)
    ↓
Any control market OPEN? → YES
    ↓
Start Week52ExtremesMonitor thread
    ↓
Poll Redis every 1s for LAST prices
    ↓
Compare to Rolling52WeekStats in DB
    ↓
Update if new high/low detected
    ↓
All markets CLOSED? → Stop monitor thread
```

### 10.3 Automatic Startup

Both the supervisor and monitor start automatically via `FutureTrading/apps.py`:

```python
class FuturetradingConfig(AppConfig):
    def ready(self):
        # Starts supervisor which manages the monitor based on market status
        from FutureTrading.services.Week52Superviror import start_52w_monitor_supervisor
        start_52w_monitor_supervisor()
```

**Supervisor logic**:
- Checks every 60 seconds if ANY control market (Tokyo, Shanghai, Bombay, Frankfurt, London, Pre_USA, USA, Toronto, Mexico) is OPEN
- If yes → starts the 52w monitor thread (idempotent)
- If all closed → stops the monitor thread to save resources
- Immediate evaluation on startup (doesn't wait 60s)

### 10.4 Database Model

`Rolling52WeekStats` (in `FutureTrading/models/extremes.py`):
- `symbol` - Future symbol (YM, ES, NQ, etc.)
- `high_52w` / `high_52w_date` - Current 52-week high and when it occurred
- `low_52w` / `low_52w_date` - Current 52-week low and when it occurred
- `last_price_checked` - Most recent price evaluated
- `all_time_high` / `all_time_low` - Optional lifetime tracking

### 10.5 Initial Setup

One-time admin setup at `http://localhost:8000/admin/FutureTrading/rolling52weekstats/`:
1. Enter initial 52w high/low values for each symbol
2. Set dates when those extremes occurred
3. Save - system auto-updates from there

The monitor auto-creates initial records if missing (using first seen price).

### 10.6 Configuration

**Disable the monitor** (useful during development/testing):
```powershell
$env:FUTURETRADING_ENABLE_52W_MONITOR = '0'
python manage.py runserver
```

**Adjust polling intervals**:
```powershell
# Monitor checks Redis every N seconds (default 1.0)
$env:FUTURETRADING_52W_MONITOR_INTERVAL = '2.0'

# Supervisor checks markets every N seconds (default 60.0)
$env:FUTURETRADING_52W_SUPERVISOR_INTERVAL = '30.0'
```

### 10.7 Symbol Mappings

Handles TOS RTD naming differences automatically:
- **RTY** (database) ↔ **RT** (Redis/Excel)
- **ZB** (database) ↔ **30YRBOND** (Redis/Excel)

### 10.8 Logging

```
📈 52-Week Extremes monitor started (interval=1.00s)
🛰️ 52w supervisor started (interval=60.0s)
🎯 [52w] YM updated: H=47683.00 (2025-11-23) L=47679.00 (2025-11-23)
💓 [52w heartbeat] tick=60 interval=1.00s last_update=YM@2025-11-23T14:30:00
🛑 52-Week Extremes monitor stop requested (all markets closed)
```

### 10.9 Frontend Integration

The RTD API automatically includes 52w data in `extended_data`:
```json
{
  "symbol": "YM",
  "last": 47682.0,
  "extended_data": {
    "high_52w": 47683.0,
    "low_52w": 47679.0,
    "dist_from_52w_high": 1.0,
    "dist_from_52w_low": 3.0
  }
}
```

Frontend displays this automatically—no changes needed.

### 10.10 Testing

Run unit tests:
```powershell
python manage.py test FutureTrading.tests.test_week52_monitor
```

Manual verification:
1. Check Django admin for `last_updated` timestamps
2. View Redis prices: `redis-cli HGETALL quotes:latest:YM`
3. Verify logs show heartbeat updates every 60s

---

## Intraday VWAP System

The VWAP (Volume-Weighted Average Price) subsystem provides both minute-by-minute session VWAP snapshots and a lightweight rolling VWAP used by the frontend for intraday visualization.

### Overview
- **Goal**: Persist accurate 1-minute VWAP progression for each tracked futures symbol and supply fast rolling VWAP values without recalculating on every request.
- **Symbols Covered**: All 11 futures plus `TOTAL` (same universe as `MarketSession`).
- **Persistence Model**: `VwapMinute` (fields include symbol, minute timestamp, last_price, cumulative_volume, computed vwap). Bid/ask removed—VWAP only requires trade price + volume.
- **Computation Source**: Live quotes + cumulative volume from Redis (Excel RTD feed currently; Schwab later).

### Minute Snapshot Logic
At (or just after) each minute boundary the capture routine:
1. Reads latest `last_price` and current cumulative volume for a symbol.
2. Calculates incremental volume: `ΔV = cumulative_volume_now - cumulative_volume_prev`.
3. Applies formula: `VWAP = Σ(price_i * ΔV_i) / Σ(ΔV_i)` across all minute slices so far in the session.
4. Writes a new `VwapMinute` row.

If no volume progress (`ΔV == 0`) the system skips the row to avoid artificial flat segments or divide-by-zero cases.

### Rolling VWAP
Some UI views need a short-horizon VWAP (e.g. last 15 minutes) separate from the full session VWAP. The rolling VWAP service:
- Pulls recent `VwapMinute` rows within the requested window (N minutes) for a symbol.
- Recomputes VWAP using only those slices (same formula but limited to window set).
- Caches result in Redis for fast reuse (key pattern: `vwap:rolling:<symbol>:<window>`).
- Updated periodically by the `IntradayMarketSupervisor` rather than on each HTTP request.

### Formula Reference
For ticks grouped into minute buckets with cumulative volumes:
```
ΔV_i = cumulative_volume_i - cumulative_volume_{i-1}
SessionVWAP_t = (Σ P_i * ΔV_i) / (Σ ΔV_i)
```
Where `P_i` is the minute's representative trade price (last price at capture) and `ΔV_i > 0`.

### Endpoints
| Endpoint | Purpose | Example |
|----------|---------|---------|
| `GET /api/vwap/today?symbol=ES` | Returns session-to-date VWAP (full accumulation) | `/api/vwap/today?symbol=ES` |
| `GET /api/vwap/rolling?symbol=ES&window=15` | Returns rolling VWAP over last N minutes | `/api/vwap/rolling?symbol=NQ&window=30` |

Responses are JSON with `{ symbol, window(optional), vwap, ts }`. Early in the session these may return `null` until at least one minute with volume completes.

### Redis Integration
- Uses existing latest quote hashes (`quotes:latest:<symbol>`) for current price & cumulative volume.
- Rolling results stored briefly in Redis to avoid repetitive database scans.
- Supervisor thread interval (~10s by default) ensures near-real-time freshness without load spikes.

### Interaction With Intraday High/Low
- High/low metrics are initialized at session open using the opening price.
- VWAP appears only after first minute completes with volume; absence of VWAP prior is expected and not an error condition.

### Operational Notes
- If cumulative volume resets mid-session (data provider glitch) the next capture treats it as a restart; integrity checks should be extended later (planned enhancement).
- Backfilling for missed minutes can be done by replaying ticks (future Parquet export process) and regenerating `VwapMinute` rows.

### Manual Verification
1. Start backend + poller (`python manage.py poll_tos_excel`).
2. Wait > 1 minute for volume accumulation.
3. Call: `curl http://127.0.0.1:8000/api/vwap/today?symbol=ES` → expect numeric `vwap`.
4. Call: `curl "http://127.0.0.1:8000/api/vwap/rolling?symbol=ES&window=15"`.
5. Compare rolling vs session VWAP—rolling should converge toward session as window increases.

### Future Enhancements
- Multiple simultaneous windows (5, 15, 30, 60) cached together.
- SSE push of VWAP deltas for smoother UI charts.
- Automatic integrity repair on volume resets.
- Bar-aligned VWAP (using generated 1m bars post ingestor rollout).

---
