# Global Markets App

The **GlobalMarkets** app is the “world clock / session engine” for Thor.

It tracks the status of a small set of **control markets** (Tokyo, Shanghai, Bombay, Frankfurt, London, Pre_USA, USA, Toronto, Mexican), computes a global composite index, and exposes APIs for the frontend and other backend apps.

> **Important:** GlobalMarkets is now **status-only**.  
> It does **not** perform any futures capturing.  
> Other apps (e.g. `FutureTrading`) subscribe to GlobalMarkets signals and do the capturing themselves.

---

## Responsibilities

GlobalMarkets is responsible for:

- Modeling the 9 **control markets** and their trading hours.
- Tracking **open / closed / preopen / preclose / holiday** states in a time-zone-aware way.
- Scheduling **status transitions** (open/close) using an event-driven monitor.
- Exposing REST APIs for:
  - Markets list & live status
  - US trading calendar (holidays)
  - Per-market data snapshots
  - User market watchlists
  - Global composite index
- Emitting **Django signals** when a market’s status changes, so other apps can react.

GlobalMarkets is **not** responsible for:

- Reading futures quotes (Redis, RTD, etc.).
- Creating futures trade sessions or any `FutureTrading` data.
- Running trading logic or risk calculations.

---

## Key Models

**Location:** `GlobalMarkets/models.py`

### `Market`

Represents a single exchange or session (the 9 control markets):

- `country` – logical name (e.g. `"Japan"`, `"USA"`, `"Canada"`, `"Mexico"`, `"Pre_USA"`)
- `timezone_name` – IANA timezone (e.g. `"Asia/Tokyo"`, `"America/New_York"`)
- `market_open_time` / `market_close_time` – local trading hours
- `status` – `"OPEN"` or `"CLOSED"` (current DB state)
- `is_control_market` – flag for the 9 control markets
- `weight` – weight in the global composite index (0.00–1.00)
- `is_active` – whether the market is tracked
- `currency` – e.g. `JPY`, `USD`, `CAD`, `MXN`
- Timestamps: `created_at`, `updated_at`

Key methods:

- `get_display_name()` – human-friendly name for UI (Tokyo, Shanghai, London, Toronto, Mexican, etc.).
- `get_sort_order()` – numeric ordering east→west; used in frontend display.
- `get_current_market_time()` – returns a dict with tz-aware date/time info:
  - `datetime`, `year`, `month`, `date`, `day`, `day_number`, `time`, `formatted_12h`, `formatted_24h`, `timestamp`, `utc_offset`, `dst_active`.
- `should_collect_data()` – helper used by snapshot collectors (not by futures capture).
- `is_market_open_now()` – returns `True` if the market is currently in its trading window (handles overnight sessions + weekends).
- `get_market_status()` – enriched status object including:
  - `current_state`: `OPEN` / `PREOPEN` / `PRECLOSE` / `CLOSED` / `HOLIDAY_CLOSED`
  - `next_open_at` / `next_close_at` (ISO tz-aware strings)
  - `next_event`: `"open"` or `"close"`
  - `seconds_to_next_event`: int seconds from now
  - plus basic fields for backward compatibility (`market_open`, `market_close`, `is_in_trading_hours`, etc.)

### `USMarketStatus`

Represents US trading days and holidays. Used by other parts of the system to know whether **US markets are open today**.

- `date`
- `is_trading_day`
- `holiday_name`
- `created_at`

Key method:

- `USMarketStatus.is_us_market_open_today()` – central helper for US trading calendar logic.

> Note: GlobalMarkets itself does **not** gate futures capture anymore; other apps can still call this helper if they want to respect US holidays.

### `MarketDataSnapshot`

Time series of market status snapshots, used for analytics / charts.

- `market` (FK)
- `collected_at`
- `market_year`, `market_month`, `market_date`, `market_day`
- `market_time`
- `market_status`
- `utc_offset`
- `dst_active`
- `is_in_trading_hours`

GlobalMarkets does **not** create these automatically; a separate collector job is expected to write snapshots using the `Market` helpers.

### `MarketHoliday`

Per-market holidays (full-day closures) used by `get_market_status()`:

- `market` (FK)
- `date`
- `name`
- `full_day`

### `GlobalMarketIndex`

Stores snapshots of the **global composite index**:

- `timestamp`
- `global_composite_score` – 0–100
- `active_markets_count`
- `session_phase` – `ASIAN`, `EUROPEAN`, `AMERICAN`, `OVERLAP`
- `contributions_json` – map of per-market contributions `{ "Tokyo": { weight, active, contribution }, ... }`

Key method:

- `GlobalMarketIndex.create_snapshot()` – calls `Market.calculate_global_composite()` and writes a new index row.

### `UserMarketWatchlist`

User-specific configuration for the world clock UI:

- `user` (FK)
- `market` (FK)
- `display_name`
- `is_primary`
- `order`
- `created_at`, `updated_at`

---

## Event-Driven Market Monitor

**Location:** `GlobalMarkets/monitor.py`  
Started from `GlobalMarkets/apps.py` (`AppConfig.ready()`).

### MarketMonitor

The `MarketMonitor` is an event-driven scheduler:

1. On startup, it loads all active control markets and **schedules the next open/close event** for each market based on `Market.get_market_status()`.
2. It uses `threading.Timer` to fire exactly at the next `open` or `close` event.
3. When a timer fires, it:
   - Recomputes `is_market_open_now()`
   - Sets `Market.status` to `"OPEN"` or `"CLOSED"`
   - Saves the `Market` row

All **side-effects** (e.g. futures capture) are handled by listeners to GlobalMarkets’ signals (see below). The monitor itself only updates `Market.status`.

On startup, `MarketMonitor` also runs a quick **reconciliation**:

- If Django restarts while a market is already open/closed and DB status is stale, it immediately corrects `Market.status` without waiting for the next timer.

---

## Signals (Status-Only)

**Location:** `GlobalMarkets/signals.py`

GlobalMarkets defines its own signals and emits them when a market’s status changes:

### Custom Signals

- `market_status_changed` – generic “status changed” event.
  - Args: `instance`, `previous_status`, `new_status`
- `market_opened` – fired when status transitions to `"OPEN"`.
  - Args: `instance`
- `market_closed` – fired when status transitions to `"CLOSED"`.
  - Args: `instance`

### Signal Handler

`on_market_status_change` (post_save for `Market`):

- Ignores newly created rows.
- Loads the previous `Market` state from the DB.
- If `status` actually changed:
  - Logs the transition (`prev → new`)
  - Sends `market_status_changed`
  - Sends `market_opened` if new status is `"OPEN"`
  - Sends `market_closed` if new status is `"CLOSED"`

> There is **no** direct import or call to `FutureTrading` or any capture logic here.  
> Other apps (e.g. `FutureTrading`) should import these signals and attach their own receivers.

Example (in another app):

```python
from django.dispatch import receiver
from GlobalMarkets.signals import market_opened

@receiver(market_opened)
def handle_market_opened(sender, instance, **kwargs):
    # Example: trigger futures capture here
    ...

Management Commands

Location: GlobalMarkets/management/commands

seed_markets.py

Seeds the 9 global control markets with correct timezones, hours, currencies, and weights.

    Creates or updates:

        Japan, China, India, Germany, United Kingdom, Pre_USA, USA, Canada, Mexico

    Deactivates any other markets.

    Ensures total weight = 100%.

Typical usage:

python manage.py seed_markets

monitor_markets.py (debug / legacy helper)

A CLI tool that polls markets at a fixed interval and keeps Market.status in sync:

    Checks each active control market.

    Uses is_market_open_now() to decide target status.

    Updates Market.status if needed.

    Does not trigger any futures capture directly; changes propagate via signals.

Typical usage in development:

python manage.py monitor_markets --interval 60
# or one-time check
python manage.py monitor_markets --once

In production, the preferred mode is the event-driven scheduler in monitor.py, not this polling command.

REST API

Location: GlobalMarkets/views/viewsets.py, GlobalMarkets/views/composite.py, GlobalMarkets/urls.py

Router-based endpoints

    GET /api/global-markets/markets/

        Returns all markets (usually the 9 control markets) with:

            country, display_name, timezone_name, market_open_time, market_close_time

            status, is_active, currency

            weight, is_control_market

            current_time (from get_current_market_time())

            market_status (from get_market_status())

            sort_order, created_at, updated_at

    GET /api/global-markets/markets/active_markets/

        Only markets where is_active=True and status='OPEN'.

    GET /api/global-markets/markets/live_status/

        Live status for all active markets.

    GET /api/global-markets/us-market-status/

    GET /api/global-markets/us-market-status/today_status/

    GET /api/global-markets/us-market-status/upcoming_holidays/

    GET /api/global-markets/market-snapshots/

    GET /api/global-markets/market-snapshots/latest_snapshots/

    GET /api/global-markets/market-snapshots/market_history/?market_id=...&hours=24

    GET/POST /api/global-markets/user-watchlist/

        User-specific watchlists (UserMarketWatchlistViewSet).

Function-based endpoints

    GET /api/global-markets/stats/ (worldclock_stats)

        Summary for the WorldClock UI:

            us_market_open

            total_markets

            active_markets

            total_snapshots

            total_users_with_watchlists

            recent_snapshots (last 24h)

            currently_trading (list of markets currently in trading hours)

    GET /api/global-markets/control-markets/ (control_markets)

        Returns exactly the 9 control markets, including DB or default config, and whether they’re currently open.

    GET /api/global-markets/composite/ (composite_index)

        Returns weighted global composite index based on active control markets.

Frontend Expectations

The React “Global Markets” table expects:

    A list of markets in east→west order, usually via:

        GET /api/global-markets/markets/ or GET /api/global-markets/control-markets/

    For each row, fields for:

        Market name – display_name / country (Tokyo, Shanghai, Bombay, Frankfurt, London, Pre_USA, USA, Toronto, Mexican)

        Year / Month / Date / Day – from market_status.current_time or current_time

        Open / Close times – market_open_time, market_close_time

        Current time – from current_time['formatted_24h'] or current_time['time']

        Status – status (OPEN/CLOSED) and/or market_status.current_state

The backend changes described here do not alter:

        The model fields,

        The serializer output,

        Or the endpoint URLs.

GlobalMarkets remains UI-compatible while gaining a cleaner, decoupled backend design.

Integration With Other Apps

    GlobalMarkets is intentionally decoupled from the futures trading logic.

    Other apps (e.g. FutureTrading) should:

        Import signals from GlobalMarkets.signals (market_opened, etc.)

        Attach their own receivers to trigger futures captures or analytics.

    This separation keeps the GlobalMarkets app reusable and easier to reason about:

        It owns time, status, and calendars.

        Consumers own captures and trading decisions.

flowchart TB

    %% -------------------------------------------------------
    %% SECTION: APPLICATION STARTUP
    %% -------------------------------------------------------
    subgraph STARTUP[Application Startup]
        direction TB
        A[Django Application Starts]
        B[GlobalMarkets AppConfig.ready()]
        C[[Load Signals]]
        D[[Start MarketMonitor]]
        A --> B --> C --> D
    end

    %% -------------------------------------------------------
    %% SECTION: MARKET MONITOR (EVENT SCHEDULER)
    %% -------------------------------------------------------
    subgraph MONITOR[Event-Driven Market Scheduler]
        direction TB

        D --> E[Initialize MarketMonitor]
        E --> F[Load Active Control Markets]

        F --> G[Schedule Next Open/Close Event<br/>(Per Market)]
        G --> H[[Timer Fires at Exact Event Time]]

        H --> I[Evaluate Real-Time State<br/>(is_market_open_now)]
        I --> J{State Changed?}

        J -->|No| K[No Action]
        J -->|Yes| L[Update market.status<br/>and Save to DB]
    end

    %% -------------------------------------------------------
    %% SECTION: STATUS SIGNALS
    %% -------------------------------------------------------
    subgraph SIGNALS[Status Signals]
        direction TB

        L --> S1[[post_save Triggered]]
        S1 --> S2{Status Actually Changed?}

        S2 -->|No| K

        S2 -->|Yes| S3[Emit<br/>market_status_changed]

        S3 --> S4[If OPEN → Emit market_opened]
        S3 --> S5[If CLOSED → Emit market_closed]
    end

    %% -------------------------------------------------------
    %% SECTION: RECONCILIATION
    %% -------------------------------------------------------
    subgraph RECON[Startup Reconciliation]
        direction TB

        D --> R1[Reconcile DB State<br/>with Real Market Timings]
        R1 --> R2{Mismatch?}
        R2 -->|No| K
        R2 -->|Yes| L
    end

    %% -------------------------------------------------------
    %% SECTION: REST API
    %% -------------------------------------------------------
    subgraph API[REST API Layer]
        direction TB

        AA[MarketViewSet<br/>Control Markets<br/>Composite Index<br/>WorldClock Stats]
        AB[Serializers Produce Structured<br/>Market & Status Data]

        AA --> AB
    end

    %% -------------------------------------------------------
    %% SECTION: FRONTEND CONSUMERS
    %% -------------------------------------------------------
    subgraph FRONTEND[Frontend Consumers]
        AC[React Global Markets Dashboard]
        AB --> AC
    end

    %% -------------------------------------------------------
    %% SECTION: EXTERNAL APP CONSUMERS
    %% -------------------------------------------------------
    subgraph EXTERNAL[External App Integrations]
        direction TB
        Z1[Subscribe to market_opened]
        Z2[Subscribe to market_closed]
        Z3[Downstream Logic:<br/>e.g. Futures Capturing,<br/>Analytics, Alerts]
        Z1 --> Z3
        Z2 --> Z3
    end

    %% SIGNALS TO EXTERNAL
    S4 --> Z1
    S5 --> Z2

What this flowchart conveys
✔ Professional modular breakdown:

Startup

Event-driven scheduler

Status-change signals

Reconciliation

API layer

Frontend

External consumers

✔ Clean cause-effect relationships:

Monitor updates status

Status emits signals

React UI reads status

Other backend apps respond to signals

✔ Reflects new decoupled design:

No capture logic in GlobalMarkets

Signals-only communication

FutureTrading handles its own capture