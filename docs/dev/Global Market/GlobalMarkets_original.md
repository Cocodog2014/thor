Updated 11/28/2025

GlobalMarkets Module

Centralized controller for:

Which markets exist

When they are open or closed

Whether futures should be captured

The global composite sentiment index

Single source of truth:
FutureTrading and other apps do not decide when to capture.
They listen to GlobalMarkets via status changes and signals.

1. High-level architecture
Responsibilities

Define the 9 control markets (Tokyo, Shanghai, Bombay, Frankfurt, London, Pre_USA, USA, Toronto, Mexico).

Track whether US markets are trading today (holidays/weekends).

Maintain per-market status (OPEN / CLOSED) and trading hours.

Provide precise open/close scheduling via an event-driven monitor.

Emit signals when markets change status so other apps can react.

Expose REST APIs for UI (world clock, composite, watchlists, etc.).

What GlobalMarkets does not do

It does not compute futures prices, indicators, or backtests.

It does not write into FutureTrading.MarketSession directly.

It does not run intraday high/low loops itself.

Those are done in FutureTrading, which listens to GlobalMarkets.

2. Control Markets & Weights

The 9 control markets and their global influence weights are defined in GlobalMarkets.models.CONTROL_MARKET_WEIGHTS and seed_markets.py:

CONTROL_MARKET_WEIGHTS = {
    'Japan': 0.25,
    'China': 0.10,
    'India': 0.05,
    'Germany': 0.20,
    'United Kingdom': 0.05,
    'Pre_USA': 0.05,
    'USA': 0.25,
    'Canada': 0.03,
    'Mexico': 0.02,
}


The seed_markets management command:

python manage.py seed_markets


Creates/updates those 9 markets with:

timezone_name

market_open_time / market_close_time

currency

weight

is_control_market = True

is_active = True

Deactivates any other Market rows not in the control list.

Use this to keep the DB in sync with the canonical config.

3. Core models
3.1 Market

Represents a single global market (Tokyo, London, USA, etc.).

Key fields:

Identity / schedule

country – logical name used everywhere ('USA', 'Germany', etc.)

timezone_name – tz database name ("Europe/London", "America/New_York")

market_open_time, market_close_time – local trading hours

Status and control

status – 'OPEN' or 'CLOSED' (drives data collection)

is_control_market – one of the 9 global drivers

weight – decimal 0.00–1.00; used in composite index

is_active – whether this market participates in scheduling

Futures capture flags (for FutureTrading)

enable_futures_capture – if False, never write MarketSession rows

enable_open_capture – if False, skip open capture for this market

enable_close_capture – if False, skip close capture for this market

Misc

currency, created_at, updated_at

Important methods:

get_display_name() – maps country → human label (e.g. 'USA' → 'USA', 'United Kingdom' → 'London').

get_sort_order() – east→west ordering (Japan = 1 … Mexico = 9).

get_current_market_time() – returns tz-aware local time info dict (year, month, date, weekday, formatted time, DST flag, etc.).

is_market_open_now() – true if local time is between open and close on a trading day.

should_collect_data() – gate used by downstream systems; returns true only if:

is_active is true,

status == 'OPEN',

weekday and not a full-day holiday.

get_market_status() – enriched status used by UI & scheduler (see below).

calculate_global_composite() (class method) – compute weighted global index (0–100) based on which control markets are currently open.

_determine_session_phase() (class method) – classify UTC time into ASIAN, EUROPEAN, AMERICAN, or OVERLAP.

get_market_status()

Returns a dict containing, for a given market:

current_state – OPEN | PREOPEN | PRECLOSE | CLOSED | HOLIDAY_CLOSED

next_open_at / next_close_at – ISO tz-aware datetimes

next_event – 'open' or 'close'

seconds_to_next_event – int seconds until the next event

is_holiday_today – per-market holiday flag

Backwards-compatible fields:

country, timezone, current_time

market_open, market_close

is_in_trading_hours

status (DB status)

should_collect_data

This method is the single source of scheduling truth and is used by the event-driven monitor.

3.2 USMarketStatus

Controls whether we collect any data on a given date.

date – unique per calendar day

is_trading_day – if False, we treat it like a holiday (no collection)

holiday_name

Important class methods:

us_market_holidays(year) – calculates the full US holiday calendar (NYSE rules, with observed dates).

is_us_market_open_today():

Checks DB override (USMarketStatus row for today), else

Checks weekend, else

Checks computed holiday set.

If is_us_market_open_today() returns False, we do not collect data and global monitors may simply idle.

3.3 MarketDataSnapshot

Periodic snapshot of the world clock status, primarily for UI and diagnostics.

FK to Market

Local date/time components

market_status, utc_offset, dst_active, is_in_trading_hours

Read-only via API; created programmatically.

3.4 GlobalMarketIndex

Historical time series of the global composite index:

global_composite_score – -100 to +100 coherence score

asia_score, europe_score, americas_score

Breadth metrics (markets open/bullish/bearish/neutral)

3.5 UserMarketWatchlist

Per-user watchlist ordering and customization:

FK user, FK market

display_name, is_primary, order

Enforces one primary market per user.

4. Scheduling & Monitoring
4.1 Event-driven MarketMonitor (preferred)

Defined in GlobalMarkets.monitor and started from GlobalMarkets.apps.GlobalMarketsConfig.ready() (unless disabled):

On Django startup (except during migrations/tests/etc.), a background thread:

Creates a MarketMonitor singleton.

Schedules per-market timers based on Market.get_market_status().

Immediately calls _reconcile_now() to fix any stale statuses.

Key behavior:

For each active control market:

Uses get_market_status() to find seconds_to_next_event and next_event (open / close).

Arms a one-shot threading.Timer for that delay.

When the timer fires, _handle_event() runs.

_handle_event(market_id)

Reloads the Market.

Recomputes is_market_open_now() and sets:

status = 'OPEN' or 'CLOSED'.

Saves the Market → triggers the pre_save signal.

On transition to OPEN:

Calls _on_market_open(market), which:

Respects enable_futures_capture and enable_open_capture.

Imports and calls FutureTrading.views.MarketOpenCapture.capture_market_open(market) to create MarketSession rows.

Starts the Intraday Market Supervisor:

intraday_market_supervisor.on_market_open(market).

On transition to CLOSED:

Stops intraday supervisor via on_market_close(market).

Important: GlobalMarkets controls when capture happens; FutureTrading controls what is captured.

_reconcile_now()

At startup, walks all active control markets and ensures Market.status matches real-time is_market_open_now().

Fixes stale statuses without waiting for the next scheduled event.

After reconciliation, starts intraday supervisor for any markets already open.

Environment flag

Set DISABLE_GLOBAL_MARKETS_MONITOR=1 to prevent auto-start in AppConfig.ready().
Useful for tests, management commands, etc.

4.2 Legacy monitor_markets command (polling)

File: monitor_markets.py (management command)

Polls markets every N seconds, updates Market.status based on is_market_open_now(), and prints status.

Does not perform data capture; it only flips status (and thus emits signals).

Use cases:

Manual / dev diagnostics.

Can be considered legacy now that we have the event-driven scheduler.
The new MarketMonitor is the canonical mechanism.

5. Signals

Defined in GlobalMarkets.signals:

market_status_changed(instance, previous_status, new_status)

market_opened(instance)

market_closed(instance)

A pre_save handler on Market:

Compares previous.status vs instance.status.

If changed, logs it and fires:

market_status_changed, and

market_opened or market_closed as appropriate.

Other apps (like FutureTrading) can subscribe to these signals for secondary effects.
Primary capture is already triggered via the MarketMonitor in monitor.py.

6. REST API
6.1 Routers and URLs

Registered in GlobalMarkets.urls:

markets/ → MarketViewSet

us-market-status/ → USMarketStatusViewSet

market-snapshots/ → MarketDataSnapshotViewSet

user-watchlist/ → UserMarketWatchlistViewSet

stats/ → worldclock_stats

control-markets/ → control_markets

composite/ → composite_index

6.2 MarketViewSet

Default queryset: only the 9 control markets in east→west order (Japan → Mexico).

Filters: status, is_active, currency, is_control_market.

Actions:

GET /markets/control/ – active control markets.

GET /markets/active_markets/ – markets with status='OPEN'.

GET /markets/live_status/ – enriched status for all active markets (gated by USMarketStatus.is_us_market_open_today()).

6.3 Control Markets & Composite endpoints

Defined in views/composite.py.

GET /control-markets/

Returns the 9 control markets with:

country, display_name

timezone_name, market_open_time, market_close_time

is_open_now

is_control_market, weight

has_db_record

Uses DB Market rows when present; otherwise falls back to static defaults (CONTROL_MARKETS_DEFAULTS).

GET /composite/

If any DB control markets exist:

Uses Market.calculate_global_composite() and returns:

composite_score (0–100)

active_markets, total_control_markets

max_possible

session_phase (ASIAN/EUROPEAN/AMERICAN/OVERLAP)

contributions per market

timestamp

Else:

Computes a simple fallback composite using static defaults and _is_open_now().

6.4 Other endpoints

worldclock_stats – high-level stats for UI (total markets, how many open, snapshots in last 24h, etc.).

MarketDataSnapshotViewSet.latest_snapshots – latest snapshot per market.

MarketDataSnapshotViewSet.market_history – history for one market.

UserMarketWatchlistViewSet – CRUD and reordering for user watchlists.

debug_market_times – diagnostic endpoint for market ordering and time calculations.

sync_markets – deprecated; kept for compatibility but no-ops in favor of the control markets config.

7. Admin UI

Admin classes are defined in GlobalMarkets.admin.

MarketAdmin

List columns: country, timezone, hours, status, is_active, currency, capture flags.

Custom “Live Status” column:

Shows TRADING / AFTER HOURS / CLOSED based on:

status

is_market_open_now()

Important:
All decisions about capture behavior are taken from:

enable_futures_capture

enable_open_capture

enable_close_capture

is_active

status

This is the main place to flip markets on/off and control how FutureTrading behaves.

USMarketStatusAdmin

Manages trading days and holidays (with date read-only once created).

Snapshot & Watchlist admins

MarketDataSnapshotAdmin – read-only, for viewing snapshot history.

UserMarketWatchlistAdmin – manage per-user watchlists.

8. How FutureTrading integrates

GlobalMarkets decides:

Is today a US trading day? (USMarketStatus.is_us_market_open_today())

For each control market:

When does it open/close? (get_market_status())

What is Market.status (OPEN / CLOSED)?

MarketMonitor:

Schedules open/close events.

On open:

Ensures Market.status = 'OPEN'.

Calls _on_market_open(market):

Honors enable_futures_capture and enable_open_capture.

Calls capture_market_open(market) in FutureTrading.

Starts IntradayMarketSupervisor.

On close:

Sets Market.status = 'CLOSED'.

Stops supervisor and lets FutureTrading finalize metrics.

Signals:

market_status_changed, market_opened, market_closed are emitted before save and can be used for additional side effects if needed.

Bottom line: GlobalMarkets is the scheduling brain; FutureTrading is the analytics engine.

9. Typical operational flow (summary)

Night before / deployment:

Run python manage.py seed_markets to ensure the 9 control markets exist and are configured.

Maintain USMarketStatus rows (or rely on computed holidays).

Django starts:

GlobalMarketsConfig.ready() imports signals.

Unless disabled, it starts the MarketMonitor in a background thread.

Monitor schedules timers and reconciles any stale statuses.

For any market already in hours, it:

Flips status to OPEN,

Starts intraday supervisor,

Triggers futures open capture.

During the day:

At each market’s open/close boundary, the monitor:

Updates Market.status,

Emits signals,

Starts/stops capture & intraday supervisor as appropriate.

Frontend:

Hits markets/, control-markets/, composite/, stats/, etc.,
to render world clocks, status cards, and composite gauges.