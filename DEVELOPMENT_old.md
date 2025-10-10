# Thor Development Guide

## Architecture Overview

Thor is a financial trading and analytics platform built with Django (backend) and React + Vite (frontend). It ingests live quotes from multiple sources, fans them through Redis for low-latency delivery, persists to Postgres for durability, and exports Parquet for ML/backtests.

### Core Architectural Principles

1. Live inputs are independent and normalized into a single quote event contract.
2. Redis is the real-time bus (Streams for replay + latest-hash for snapshots).
3. Django is the single API/UI surface; the frontend never talks directly to Redis or external providers.
4. Postgres is the durable store; Parquet exports power ML/backtests with DuckDB/Polars.
5. A World Clock in Django drives market-aware triggers and schedules.

## Application Structure

```
thor-backend/
├── SchwabLiveData/          # Live Data providers (Excel RTD via xlwings, JSON, Schwab API)
│   ├── providers.py         # Provider implementations & precision rules
│   ├── excel_live.py        # RTD bridge with Excel (Windows)
│   └── provider_factory.py  # Provider selection logic
├── futuretrading/           # Business logic (signals, weights, derived metrics)
│   ├── models.py            # TradingInstrument, MarketData, TradingSignal, etc.
│   └── services/            # e.g., classification.py
├── timezones/               # World Clock & scheduling
│   ├── models.py            # Market hours & holidays
│   └── views.py             # World Clock/session endpoints
├── thordata/                # Historical data & backtests
│   ├── models.py            # Historical storage & analytics
│   └── services/            # Exporters, backtest engines
└── thor_project/            # Django settings & wiring

thor-frontend/
├── src/
│   ├── pages/
│   │   └── FutureTrading/   # Main dashboard
│   ├── components/         # Reusable UI components  
│   └── services/          # API client logic
└── package.json
```

## Responsibility Matrix

### SchwabLiveData App - "Data Source Truth"
Owns raw data collection and display formatting at the edge; normalizes into the canonical quote event.

- ✅ Live Data Providers
  - Thinkorswim via Excel RTD (xlwings script)
  - Schwab API (JSON HTTP/Web)
  - Excel File (openpyxl) and JSON mock (for dev/testing)

- ✅ Data Formatting
  - Symbol-specific display precision (YM=0, ES=2, SI=3, etc.)
  - Price rounding and string conversion
  - Field standardization (bid/ask/last/volume)
  - Symbol normalization map across sources

- ✅ Publishing
  - Publishes canonical events to Redis Streams and updates latest-hash per symbol
  - Provider health checks and status

- ❌ Does NOT Handle
  - Signal classification (Strong Buy/Sell/Hold)
  - Statistical value calculations
  - Contract weighting formulas
  - Composite score computations

### FuturesTrading App - "Business Logic Truth"
Owns all trading formulas and derived calculations.

- ✅ Trading Models
  - TradingInstrument, TradingSignal, MarketData
  - SignalStatValue (maps signals to numeric values)
  - ContractWeight (instrument weighting factors)
  - HbsThresholds (classification boundaries)

- ✅ Classification Formulas (services/classification.py)
  - Net change → Signal mapping (Strong Buy/Buy/Hold/Sell/Strong Sell)
  - Statistical value lookups per instrument
  - Weighted composite calculations

- ✅ API Endpoints
  - `/api/quotes` - Snapshot quotes (reads Redis latest-hash)
  - `/api/quotes/stream` - Server-Sent Events (tails unified Redis Stream)
  - Strategy and signal endpoints (future)

- ❌ Does NOT Handle
  - Raw data collection
  - Display precision decisions
  - Provider selection logic
  - Deployment timing or scheduling
  - Historical data backtesting

### Timezones App - "World Clock & Scheduling"
Owns market calendars, open/close, and scheduling triggers.

- ✅ Market Timing
  - Market open/close schedules per exchange
  - Trading session awareness (pre-market, regular, after-hours)
  - Holiday calendar management
  - Timezone conversions for global markets

- ✅ Deployment Control
  - Feature deployment schedules
  - Market-hours-aware feature activation
  - Rollback timing windows
  - Maintenance window scheduling

- ✅ Time-Based Logic
  - When to start/stop data collection
  - When to activate trading signals
  - When to send alerts or notifications
  - Session-based feature toggles

- ❌ Does NOT Handle
  - Trading calculations or formulas
  - Raw data formatting
  - User interface logic
  - Historical data analysis

### Thordata App - "Backtesting & Historical Analysis"
Owns historical data processing and backtesting functionality.

- ✅ Historical Data Management
  - Historical price data storage and retrieval
  - Data archiving and compression
  - Historical market data APIs
  - Data quality validation and cleaning

- ✅ Backtesting Engine
  - Strategy backtesting framework
  - Historical signal generation
  - Performance metrics calculation
  - Risk analysis and drawdown calculations

- ✅ Analysis Tools
  - Historical pattern recognition
  - Statistical analysis of trading strategies
  - Performance comparison tools
  - Portfolio simulation capabilities

- ✅ API Endpoints
  - Historical data retrieval APIs
  - Backtesting execution endpoints
  - Performance reporting APIs
  - Strategy comparison tools

- ❌ Does NOT Handle
  - Live data collection or formatting
  - Real-time signal generation
  - Deployment timing or scheduling
  - Current market data processing

## Data Flow Architecture

### Live Data Flow
```
TOS → Excel (RTD) → xlwings (collector) → Redis
Schwab API (collector) → Redis

Redis → Django: /api/quotes (snapshot) and /api/quotes/stream (SSE)
Django → Frontend: React subscribes to SSE/REST only

World Clock (Django) → Market Triggers → start/stop ingest & exports
```

### Historical Data Flow
```
Unified stream → Ingestor → Postgres (ticks)
Scheduled job → Export Parquet (partitioned by date/symbol)
DuckDB/Polars → Training & Backtests → Results
```

### Combined Flow
1. World Clock determines session state and triggers start/stop.
2. Collectors publish canonical events to Redis Streams and update latest cache.
3. Django serves snapshots and SSE from Redis; optional aggregator merges sources.
4. Ingestor batches events into Postgres; scheduled jobs export Parquet.
5. ML/backtests consume Parquet; frontend shows live/session status from Django.
```

## Development Setup

### Backend (Django)

1. **Environment Setup**
   ```powershell
   cd A:\Thor\thor-backend
   .\venv\Scripts\Activate.ps1
   ```

2. **Environment Variables**
   ```powershell
  # Primary data sources (collectors)
  $env:DATA_PROVIDER = 'excel_live'  # or 'json', 'schwab'

  # Excel Live settings (Windows)
  $env:EXCEL_DATA_FILE = 'A:\\Thor\\CleanData.xlsm'
  $env:EXCEL_SHEET_NAME = 'Futures'
  $env:EXCEL_LIVE_RANGE = 'A1:M20'
  $env:EXCEL_LIVE_REQUIRE_OPEN = '0'  # allows background read from closed workbook

  # Redis (live bus)
  $env:REDIS_URL = 'redis://localhost:6379/0'

  # Postgres (durable store)
  $env:DB_NAME = 'thor_db'
  $env:DB_USER = 'postgres'
  $env:DB_PASSWORD = 'postgres'
  $env:DB_HOST = 'localhost'
  $env:DB_PORT = '5432'
   ```

3. **Database Setup**
   ```powershell
   python manage.py migrate
   python manage.py seed_stat_values --create-instruments
   ```

4. **Start Server**
   ```powershell
   python manage.py runserver
   ```

### Frontend (React + Vite)

1. **Setup**
   ```powershell
   cd A:\Thor\thor-frontend
   npm install
   ```

2. **Development Server**
   ```powershell
   npm run dev
   ```

3. **Access URLs**
   - Frontend: http://localhost:5173
   - Backend API: http://127.0.0.1:8000/api/
   - Admin: http://127.0.0.1:8000/admin/

## API Endpoints

### Live Quotes Endpoints
- `GET /api/quotes?symbols=AAPL,ES,YM` — Snapshot from Redis latest-hash
- `GET /api/quotes/stream` — Server-Sent Events (stream of quote events + heartbeats)
- `GET /api/session` — World Clock: open/closed, next_transition_at, holiday info

## Development Patterns

### Adding New Data Fields

**For Raw Data Fields (prices, volumes, etc.):**
1. Update SchwabLiveData providers
2. Add to provider data structure
3. Handle formatting/precision rules

**For Derived Fields (signals, ratios, etc.):**
1. Update FuturesTrading models/services
2. Add to classification.py or new service module
3. Enrich in LatestQuotesView

### Collector Development (Providers)

Adding new sources:
1. Implement a collector that emits the canonical quote event.
2. Publish to Redis Streams (`quotes:stream:<source>`) and update latest-hash.
3. Register provider in `SchwabLiveData/provider_factory.py` if used inside Django.
4. Add precision rules and symbol normalization at the edge.

### Formula Development

**Adding New Classifications:**
1. Extend `futuretrading/services/classification.py`
2. Add database models if persistent storage needed
3. Create management commands for data seeding
4. Add admin interfaces for configuration

## Testing Strategy

### SchwabLiveData Testing
- Test each provider independently
- Mock external data sources (Excel, APIs)
- Verify formatting consistency across providers
- Test provider fallback mechanisms

### FuturesTrading Testing
- Test classification formulas with known inputs
- Verify statistical value calculations
- Test composite score computations
- Mock SchwabLiveData responses for isolation

### Integration Testing
- End-to-end with Redis Streams + latest cache
- Frontend API contract validation (snapshot + SSE)
- Replay tests by reading from Streams and verifying idempotent DB writes

## Deployment Considerations

### Environment Configuration
- Production should use Schwab API provider
- Staging can use Excel or JSON providers
- Development defaults to Excel Live for real-time testing

### Performance Optimization
- Redis Streams maxlen (time-bounded retention) and consumer groups
- Batch size tuning for Postgres ingestion (COPY or batched INSERT)
- SSE heartbeat intervals and client backoff

### Monitoring
-- Provider health checks
-- Redis stream lag and consumer lag monitoring
-- Data freshness (no events during open hours)
-- Classification accuracy tracking

---

## Canonical Quote Event Contract (v1)

All live sources must publish this JSON shape to Redis Streams and (after merge policy) to the unified stream. Nulls allowed where fields aren’t available.

Required fields:
- symbol: string (canonicalized, e.g., ES, YM, AAPL)
- ts: string (UTC ISO8601) or number (epoch ms)
- source: string ("TOS" | "SCHWAB" | "MOCK")
- last, bid, ask: number | null
- lastSize, bidSize, askSize: number | null

Optional fields:
- condition: string | null
- venue: string | null
- seq: integer | null (monotonic within source+symbol if available)
- meta: object (free-form)

Example:
```
{
  "v": 1,
  "symbol": "ES",
  "ts": "2025-10-09T13:31:15.123456Z",
  "source": "TOS",
  "last": 5342.25,
  "bid": 5342.00,
  "ask": 5342.50,
  "lastSize": 2,
  "bidSize": 5,
  "askSize": 3,
  "seq": 184467,
  "condition": null,
  "venue": "CME",
  "meta": {"precision": 2}
}
```

### Redis Keys and Conventions
- Streams per source: `quotes:stream:<source>` (e.g., quotes:stream:TOS, quotes:stream:SCHWAB)
  - Use XADD with maxlen (time-bounded), create consumer groups for ingestors: `quotes:cgrp:ingest`
- Latest snapshot per symbol: `quotes:latest:<symbol>` (hash)
  - Fields mirror the event plus `updated_at` and `active_source`
- Unified merged stream (optional): `quotes:stream:unified` (post-merge policy)
- Small rolling per-symbol series (optional): `quotes:series:<symbol>`

### Merge Policy
If both sources provide the same symbol, prefer by:
1) highest seq if comparable; else 2) preferred source per symbol; else 3) newest ts.
Record `active_source` in latest-hash for UI transparency.

---

## Storage and ML Pipeline

- Postgres table `ticks(symbol text, ts timestamptz, last numeric, bid numeric, ask numeric, last_size int, bid_size int, ask_size int, source text, cond text, seq bigint, extra jsonb)`
- Batched ingestion from Redis Streams; idempotent upsert on (symbol, source, ts, seq)
- Nightly export Parquet partitioned by `date=YYYY-MM-DD/symbol=<SYMBOL>`
- DuckDB/Polars read Parquet for features, training, and backtests

---

## Frontend Contracts

- `/api/quotes` returns an array of snapshot records (latest-hash), includes `active_source` and `updated_at`
- `/api/quotes/stream` emits SSE with event: "quote" and data: canonical event (or merged event)
- `/api/session` returns `{ is_open, market, now, next_transition_at, holiday }`

## Future Enhancements

### SchwabLiveData Roadmap
- Full Schwab API integration
- WebSocket real-time feeds
- Multiple exchange support
- Historical data providers

### FuturesTrading Roadmap  
- Advanced signal algorithms
- Real-time risk management formulas
- Portfolio optimization tools
- Alert system integration
- Strategy performance monitoring

### Timezones Roadmap
- Market hours automation
- Deployment scheduling system
- Holiday calendar integration
- Global market timezone support
- Feature rollout timing controls

### Thordata Roadmap
- Complete backtesting framework
- Historical data ingestion pipelines
- Strategy performance analytics
- Risk-adjusted return calculations
- Portfolio simulation tools
- Monte Carlo analysis capabilities

## Common Development Tasks

### Changing Display Precision
Update the precision maps in:
- `SchwabLiveData/providers.py` (ExcelProvider)
- `SchwabLiveData/providers.py` (JSONProvider) 
- `SchwabLiveData/excel_live.py` (ExcelLiveProvider)

### Adding New Futures Contracts
1. Add to `DEFAULT_SYMBOLS` in ProviderConfig
2. Add stat values via `seed_stat_values` command
3. Add precision rules to provider precision maps
4. Configure market hours in timezones app
5. Update frontend symbol list if needed

### Modifying Classification Logic
1. Update `futuretrading/services/classification.py`
2. Adjust threshold values in database or fallback constants
3. Test with known market scenarios
4. Update admin interfaces for configuration

### Scheduling Feature Deployments
1. Define deployment windows in timezones app
2. Configure market-hours-aware activation
3. Set rollback timing constraints
4. Test deployment timing logic
5. Monitor deployment success across timezones

### Running Backtests
1. Define strategy parameters in futuretrading app
2. Load historical data via thordata app
3. Execute backtest using thordata engines
4. Analyze results through thordata APIs
5. Compare strategy performance metrics
6. Schedule regular backtest runs via timezones

---

## Quick Reference

**Start Development:**
```powershell
# Terminal 1 - Backend
cd A:\Thor\thor-backend
.\venv\Scripts\Activate.ps1
python manage.py runserver

# Terminal 2 - Frontend  
cd A:\Thor\thor-frontend
npm run dev
```

**Key Files to Know:**
- Live Data Flow: `SchwabLiveData/views.py` → `futuretrading/views.py`
- Historical Data Flow: `thordata/views.py` → `futuretrading/views.py`
- Providers: `SchwabLiveData/providers.py`, `SchwabLiveData/excel_live.py`
- Classification: `futuretrading/services/classification.py`
- Backtesting: `thordata/services/` (to be implemented)
- Frontend: `src/pages/FutureTrading/FutureTrading.tsx`
- Models: `futuretrading/models.py`, `thordata/models.py`

**Common URLs:**
- Live Data API: `/api/schwab/quotes/latest/`
- Enriched API: `/api/quotes/latest/`
- Historical Data API: `/api/thordata/` (to be implemented)
- Backtesting API: `/api/thordata/backtest/` (to be implemented)
- Admin Panel: `/admin/`
- Frontend: `http://localhost:5173`