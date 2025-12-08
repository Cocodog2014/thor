ThorTrading – Futures & Intraday Metrics Engine

Last updated: December 2025

ThorTrading is the futures / indices “brain” for the Thor stack.
It ingests live quotes (via TOS RTD → Redis), enriches them, captures market-open snapshots, computes intraday metrics, and exposes everything through APIs and Django admin.

This document describes the current architecture as it exists today – not the future GlobalMarkets integration plan.

1. High-Level Overview
Purpose

ThorTrading provides:

Real-time futures dashboard (YM, ES, NQ, RTY, CL, SI, HG, GC, VX, DX, ZB)

“Market Open” trade capture: 1 row per future + a synthetic TOTAL composite

Intraday metrics & VWAP snapshots

52-week extremes & target high/low support

APIs for the frontend (quotes, ribbons, market-open sessions)

Django admin for inspecting market-open sessions

The system is backend-driven with multiple background workers and a stateless HTTP API layer.

2. External Dependencies
Data Source: TOS Excel RTD

Configured in ThorTrading/config.py:

TOS_EXCEL_FILE – path to the Excel workbook with RTD formulas (e.g. A:\Thor\RTD_TOS.xlsm)

TOS_EXCEL_SHEET – sheet name ("LiveData")

TOS_EXCEL_RANGE – range ("A1:N13")

EXPECTED_FUTURES – expected row symbols (YM, ES, NQ, RTY, CL, SI, HG, GC, VX, DX, ZB)

The actual live quotes used in ThorTrading are typically provided via LiveData/Redis, populated from this RTD sheet by a separate process.

Redis Client

LiveData.shared.redis_client.live_data_redis
Used by:

Quote enrichment

Grading system (exit price lookup)

52-week monitor

VWAP minute capture

3. Core Concepts & Constants

Defined in ThorTrading/constants.py:

FUTURES_SYMBOLS
['YM', 'ES', 'NQ', 'RTY', 'CL', 'SI', 'HG', 'GC', 'VX', 'DX', 'ZB']

CONTROL_COUNTRIES
['Japan', 'China', 'India', 'Germany', 'United Kingdom', 'Pre_USA', 'USA', 'Canada', 'Mexico']
Used for market-open session analytics and “latest per market” views.

REDIS_SYMBOL_MAP
Maps canonical symbol → Redis key (e.g. DX → $DXY).

SYMBOL_NORMALIZE_MAP
Converts variants (DXY, $DXY, USDX, etc.) to canonical futures symbols.

4. App Startup & Background Stack
AppConfig (apps.py)
class ThorTradingConfig(AppConfig):
    name = "ThorTrading"
    verbose_name = "Thor Trading"

    def ready(self):
        ...
        auto_start = os.environ.get("THOR_STACK_AUTO_START", "1").lower() not in {"0", "false", "no"}
        if not auto_start:
            return

        from ThorTrading.services.stack_start import start_thor_background_stack
        ...
        threading.Thread(
            target=_delayed_start,
            name="ThorStackDelayedStart",
            daemon=True,
        ).start()


On Django app ready, a delayed thread is started.

Unless THOR_STACK_AUTO_START is set to 0/false/no, it calls:

start_thor_background_stack() after ~1 second.

start_thor_background_stack

Located in ThorTrading/services/stack_start.py:

Bootstraps all Thor background services (supervisors), typically including:

Excel/Redis poller for RTD data

Intraday metric supervisor

Market open capture coordinator

Market grading / VWAP minute capture

52-week extremes supervisor

Any pre-open backtest / support services

Each of these usually runs in its own thread with its own loop and sleep interval.

Important: As of now, these supervisors are independent – there is no single global heartbeat; each one has its own timing.

5. Data Models (Conceptual Overview)

Full model definitions live under ThorTrading/models. This section summarizes their roles.

5.1 TradingInstrument

Master configuration for each futures instrument:

Symbol, name, active flags

show_in_ribbon for ticker ribbon display

Optional update frequency / weights

5.2 MarketSession

Single-table design for market-open capture:

session_number, capture_group – group all rows belonging to the same market open event

Date fields: year, month, date, day

country – e.g. Japan, USA

future – underlying (YM, ES, … or TOTAL)

Price snapshot at open:

last_price, bid_price, ask_price, volume, spread

24-hour session context:

open_price_24h, prev_close_24h, open_prev_diff_24h, open_prev_pct_24h

low_24h, high_24h, range_diff_24h, range_pct_24h

52-week stats:

low_52w, high_52w, range_52w, range_pct_52w, low_pct_52w, high_pct_52w

Signal & trade intent:

bhs – BUY/HOLD/SELL (or STRONG_BUY / STRONG_SELL)

weight – signal weight

entry_price, target_high, target_low

Outcomes:

wndw – PENDING / WORKED / DIDNT_WORK / NEUTRAL

target_hit_at, target_hit_price, target_hit_type

Market open/close metrics: market_open, market_close, ranges, etc.

Backtest stats:

Additional fields populated by backtest_stats service.

5.3 Intraday & 24h Models

Martket24h (rolling 24-hour metrics)

MarketIntraDay (1-minute OHLCV bars)

SessionVolume (per-session volume tracking)

VwapMinute (per-minute VWAP snapshots)

52-week stats model (Rolling52WeekStats / extremes)

These are populated by workers (intraday supervisor, VWAP capturer, MarketGrader-VWAP integration) and are read by analytics & dashboards.

5.4 Target & Extremes

TargetHighLow / target config – admin-tuned rules controlling target_high/low offsets.

52-week extremes models – track rolling high/low, distance to extremes, etc.

6. Quote Enrichment Pipeline

Implemented in ThorTrading/services/quotes.py:

rows, total = get_enriched_quotes_with_composite()


The enrichment pipeline:

Reads latest quotes from Redis for all FUTURES_SYMBOLS.

Normalizes symbols to canonical names (SYMBOL_NORMALIZE_MAP).

Attaches:

24-hour metrics (open/prev/hi/low/range)

52-week extremes

signals (BUY/HOLD/SELL/STRONG_*)

weights and composite metrics

Computes a composite “TOTAL” signal with a weighted average of all instruments.

The resulting rows array is the canonical “live data view” used by:

Market open capture

Latest quotes API

Ribbon quotes

Close metrics (for exit reference)

This layer is stateless; it simply reflects what Redis currently has.

7. Market-Open Capture Flow

Implemented in ThorTrading/services/MarketOpenCapture.py:

Entry point
def capture_market_open(market):
    return _service.capture_market_open(market)


market is expected to be a GlobalMarkets.models.Market (or similar) with:

country

flags like enable_futures_capture and enable_open_capture

get_current_market_time() for time info.

Workflow

Guard flags

if not market.enable_futures_capture: skip
if not market.enable_open_capture: skip


Fetch enriched quotes and composite

enriched, composite = get_enriched_quotes_with_composite()


Derive time_info

time_info = market.get_current_market_time()


Determine new session_number and capture_group.

Create one MarketSession row per future (11 rows) via create_session_for_future:

Sets all snapshot prices, 24-hour metrics, 52-week metrics.

Sets bhs, weight from per-instrument signal.

Computes entry_price based on signal:

BUY/STRONG_BUY → ask_price

SELL/STRONG_SELL → bid_price

Uses compute_targets_for_symbol(symbol, entry_price) to populate target_high/target_low.

Pulls in backtest stats for that (country, future) at captured_at.

Create a synthetic TOTAL row via create_session_for_total:

Uses composite metrics (avg weight, signal, etc.).

Optionally uses YM entry price as TOTAL’s entry and computes targets.

Run metrics POST-capture

MarketOpenMetric.update(session_number) – sets market_open related fields.

CountryFutureWndwTotalsService.update_for_session_country(...) – aggregates WNDW outcomes for stats.

The capture_market_open function returns the first created MarketSession (or None on failure) and logs the capture.

Timing note:
This service assumes it is invoked at the real market open.
Today, that invocation is done by a separate “open capture” supervisor, not directly by GlobalMarkets.

8. Market Close & Range Metrics
MarketCloseCaptureView

Route:
GET /api/future-trading/market-close/capture?country=United%20States[&force=1]

Workflow:

Determine the latest session_number for country.

If market_close is already populated and force!=1, return already-closed.

Fetch a fresh snapshot of enriched quotes:

enriched, _ = get_enriched_quotes_with_composite()


Run:

MarketCloseMetric.update_for_country_on_close(country, enriched)

MarketRangeMetric.update_for_country_on_close(country)

Return summary JSON: rows updated, session number, status.

This is currently a manual/HTTP-triggered close used for manual overrides or re-runs.

9. Grading Engine (MarketGrader)

Defined in ThorTrading/services/MarketGrader.py.

Purpose

The MarketGrader continuously evaluates open trades for all futures and updates MarketSession.wndw based on whether targets/stops were hit.

Key behavior

Loop:

while self.running:
    pending_sessions = MarketSession.objects.filter(wndw='PENDING')
    for session in pending_sessions:
        self.grade_session(session)

    # also capture VWAP minutes per symbol
    ...
    time.sleep(self.check_interval)  # default 0.5 seconds


Price lookup (get_current_price):

Maps special symbols:

TOTAL → YM

DX → $DXY

Uses Redis quotes for bid, ask.

BUY/STRONG_BUY trades evaluate exit using bid.

SELL/STRONG_SELL trades evaluate exit using ask.

grade_session rules:

If missing entry/targets → mark NEUTRAL.

If signal is HOLD or empty → NEUTRAL.

Otherwise:

Longs:
current_price >= target_high → WORKED (TARGET)
current_price <= target_low → DIDNT_WORK (STOP)

Shorts:
current_price <= target_low → WORKED (TARGET)
current_price >= target_high → DIDNT_WORK (STOP)

Otherwise: leave PENDING for next loop.

On first resolution, stamps:

target_hit_at

target_hit_price

target_hit_type (TARGET/STOP)

Integrated VWAP minute capture:

On each loop, captures one VwapMinute row per symbol at the minute boundary (using last + volume).

Timing:
This engine has its own loop, independent of GlobalMarkets. It is started/stopped by the Thor stack, not by the global scheduler.

10. VWAP, 24h & Session Metrics
VWAP Precompute

Command/service to sample quotes and populate VwapMinute.

Some of this is integrated directly in MarketGrader; others via a dedicated capture_vwap_minutes script.

24-Hour & Session Metrics

Services under services/:

update_24h_for_country – keeps 24-hour session rows in sync with live data.

update_intraday_bars_for_country – maintains 1-minute OHLCV bars.

update_session_volume_for_country – adds intraday volume context.

session_open, session_high_low, session_close_range – compute open, high/low, close, and session range metrics.

These are typically invoked by the intraday supervisor or dedicated workers on per-second or per-minute loops.

11. 52-Week Extremes & Target High/Low
52-Week Supervisor

Monitors quotes via Redis to update rolling 52-week stats.

Has its own loop/timing.

Note: It is the one place that checks GlobalMarkets to see if any control markets are open, to decide whether to run or pause – but its internal tick is still independent.

TargetHighLow

Admin-configured rules for target offsets per symbol.

Used by MarketOpenCaptureService and TOTAL/individual futures to compute target_high and target_low.

12. API Layer (REST Endpoints)

Defined in ThorTrading/urls.py + view modules.

12.1 Real-Time Quotes

Base URL: .../api/ThorTrading/ (prefix depends on project router)

GET quotes/latest → LatestQuotesView

Returns:

rows: enriched per-instrument data (quotes + signals + metrics)

total: composite “TOTAL” metrics

GET quotes/ribbon → RibbonQuotesView

Filters enriched rows to instruments with show_in_ribbon=True.

Returns:

symbols: array of minimal quote/label/signal for ribbon

count

last_updated

12.2 Market Open Sessions

All backed by MarketSession and serializers.

GET market-opens/ → MarketOpenSessionListView

Optional filters: country, status, date=YYYY-MM-DD.

GET market-opens/<pk>/ → MarketOpenSessionDetailView

Detailed single row view.

GET market-opens/today/ → TodayMarketOpensView

All sessions captured today.

GET market-opens/pending/ → PendingMarketOpensView

All sessions with wndw='PENDING'.

GET market-opens/stats/ → MarketOpenStatsView

Overall counts, win rate, by-market breakdown, last 7-day performance.

GET market-opens/latest/ → LatestPerMarketOpensView

For each CONTROL_COUNTRIES member, returns the latest session (today if present, otherwise most recent prior).

12.3 Market Close Capture

GET market-close/capture?country=...&force=0|1 → MarketCloseCaptureView

Manual/override endpoint to finalize market_close and range metrics.

All MarketOpen* views also have backwards-compatible aliases (MarketSession*View), but the URLs above are the canonical ones.

13. Django Admin – Market Sessions

Custom admin template:

marketsession.css – sticky headers, scroll sync, highlighting.

marketsession.js – enhances list view UX.

change_list.html – plugs assets into the MarketSession change list.

This admin UI is the primary tool for inspecting:

per-session futures rows

trade outcomes (wndw)

open/close metrics

per-country performance over time

14. Timing Summary (Current State)

As implemented today:

ThorTrading uses multiple independent loops:

Intraday supervisor (1s)

MarketGrader (0.5s)

VWAP capturer (60s)

52-week monitor

Open/close capture supervisors

GlobalMarkets is only lightly touched (mainly by 52-week monitor and via market object passed into capture_market_open), but does not drive the core timing.

APIs (quotes/latest, market-opens/*) are stateless and depend on the frontend’s polling strategy.

A future refactor can unify all of this under a single GlobalMarkets-driven heartbeat and a frontend GlobalTimerProvider, but this document reflects the current behavior and design.