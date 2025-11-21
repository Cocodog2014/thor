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
