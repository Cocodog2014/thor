# Legacy Supervisor Starters - Disabled for Heartbeat Mode

## Summary
All legacy supervisor starters now check `THOR_SCHEDULER_MODE` environment variable before spawning threads. When the mode is `"heartbeat"` (default), legacy supervisors are completely bypassed, preventing race conditions with the unified heartbeat scheduler.

## Disabled Entry Points

### 1. **globalmarkets_hooks.py** ✅
- **Function**: `_start_global_background_services()` (line 73)
- **Function**: `_stop_global_background_services()` (line 86)
- **What it did**: Started/stopped VWAP and 52-week monitor services
- **Now**: Checks `THOR_SCHEDULER_MODE` and returns early if `"heartbeat"`
- **Trigger**: Called on `market_opened` signal (bootstrap_open_markets, handle_market_opened)

```python
def _start_global_background_services():
    """Start VWAP and 52-week services, but only if NOT in heartbeat scheduler mode."""
    scheduler_mode = os.environ.get("THOR_SCHEDULER_MODE", "heartbeat").lower()
    if scheduler_mode == "heartbeat":
        logger.debug("Skipping legacy VWAP/52w starters (heartbeat scheduler mode active)")
        return
    # ... original code only runs in legacy mode
```

### 2. **stack_start.py** ✅
- **Function**: `start_preopen_backtest_supervisor_wrapper()` (line 87)
- **What it did**: Spawned PreOpenBacktestSupervisor thread
- **Now**: Checks `THOR_SCHEDULER_MODE` and returns early if `"heartbeat"`
- **Trigger**: Called by `start_thor_background_stack()` during Django startup

```python
def start_preopen_backtest_supervisor_wrapper():
    scheduler_mode = os.environ.get("THOR_SCHEDULER_MODE", "heartbeat").lower()
    if scheduler_mode == "heartbeat":
        logger.debug("Skipping legacy Pre-open Backtest supervisor (heartbeat scheduler mode active)")
        return
    # ... original code only runs in legacy mode
```

### 3. **Supervisor start() Methods** ✅
All individual supervisor classes also have heartbeat guards:

#### Week52Supervisor.py (line 45)
```python
def start(self):
    scheduler_mode = os.getenv("THOR_SCHEDULER_MODE", "heartbeat").lower()
    if scheduler_mode == "heartbeat":
        logger.info("Heartbeat scheduler active; skipping legacy 52w extremes monitor")
        return
    # ... original start code
```

#### vwap_capture.py - VWAPMinuteCaptureService (line 83)
```python
def start(self) -> bool:
    scheduler_mode = os.getenv("THOR_SCHEDULER_MODE", "heartbeat").lower()
    if scheduler_mode == "heartbeat":
        logger.info("Heartbeat scheduler active; skipping legacy VWAP capture thread")
        return False
    # ... original start code
```

#### PreOpenBacktestSupervisor.py (line 50)
```python
def start(self):
    scheduler_mode = os.getenv("THOR_SCHEDULER_MODE", "heartbeat").lower()
    if scheduler_mode == "heartbeat":
        logger.info("Heartbeat scheduler active; skipping legacy pre-open backtest supervisor")
        return
    # ... original start code
```

#### IntradayMarketSupervisor.on_market_open() (line 65) / on_market_close() (line 98)
```python
def on_market_open(self, market):
    scheduler_mode = os.getenv("THOR_SCHEDULER_MODE", "heartbeat").lower()
    if scheduler_mode == "heartbeat":
        logger.info("Heartbeat scheduler active; skipping legacy intraday worker for %s", ...)
        return
    # ... original code
```

## Architecture Impact

### Startup Flow - HEARTBEAT MODE (default)
```
Django starts
    ↓
AppConfig.ready()
    ├─ Loads active_markets signal listeners
    ├─ THOR_SCHEDULER_MODE = "heartbeat" (default)
    └─ Bootstrap signal fires
        ├─ bootstrap_open_markets()
        │   ├─ intraday_market_supervisor.on_market_open() → RETURNS EARLY
        │   └─ _start_global_background_services() → RETURNS EARLY
        └─ start_thor_background_stack()
            ├─ start_preopen_backtest_supervisor_wrapper() → RETURNS EARLY
            └─ other supervisors (MarketOpenCapture, Schwab poller)
```

### Startup Flow - LEGACY MODE (opt-in)
```
Django starts with THOR_SCHEDULER_MODE=legacy
    ↓
AppConfig.ready()
    ├─ Loads active_markets signal listeners
    ├─ THOR_SCHEDULER_MODE = "legacy" (env set)
    └─ Bootstrap signal fires
        ├─ bootstrap_open_markets()
        │   ├─ intraday_market_supervisor.on_market_open() → SPAWNS THREAD
        │   └─ _start_global_background_services() → SPAWNS VWAP + 52w THREADS
        └─ start_thor_background_stack()
            └─ start_preopen_backtest_supervisor_wrapper() → SPAWNS THREAD
```

## Heartbeat Scheduler Entry Point

The replacement for all these legacy starters is:

```bash
python manage.py run_heartbeat [--fast-tick 1.0] [--slow-tick 60.0]
```

This:
1. Sets `THOR_SCHEDULER_MODE=heartbeat` automatically
2. Acquires Redis leader lock (optional, default enabled)
3. Registers all 8 jobs via `register_all_jobs(registry)`
4. Runs unified heartbeat loop

## Heartbeat Jobs (Replacing Legacy Supervisors)

| Job | Interval | Replaces |
|-----|----------|----------|
| IntradayJob | 1s | intraday_supervisor worker threads |
| Week52ExtremesJob | 2s | Week52Supervisor thread |
| SessionVolumeJob | 10s | (new, no legacy equiv) |
| MarketMetricsJob | 10s | (new, no legacy equiv) |
| TwentyFourHourJob | 30s | (new, no legacy equiv) |
| PreOpenBacktestJob | 30s | PreOpenBacktestSupervisor thread |
| VwapMinuteCaptureJob | 60s | VWAPMinuteCaptureService thread |
| ClosedBarsFlushJob | 60s | (new, no legacy equiv) |

## Environment Variable Reference

**THOR_SCHEDULER_MODE**
- Default: `"heartbeat"`
- Options: `"heartbeat"` or `"legacy"`
- Set by: `run_heartbeat` command automatically
- Checked in: All supervisor start() methods and wrapper functions

## Verification Checklist

- [x] globalmarkets_hooks.py: `_start_global_background_services()` guarded
- [x] globalmarkets_hooks.py: `_stop_global_background_services()` guarded
- [x] stack_start.py: `start_preopen_backtest_supervisor_wrapper()` guarded
- [x] Week52Supervisor.py: `start()` method guarded
- [x] vwap_capture.py: `VWAPMinuteCaptureService.start()` guarded
- [x] PreOpenBacktestSupervisor.py: `start()` method guarded
- [x] intraday_supervisor/supervisor.py: `on_market_open()` guarded
- [x] intraday_supervisor/supervisor.py: `on_market_close()` guarded
- [x] All legacy starters use consistent env var check pattern
- [x] All use `.lower()` to handle case variations

## Testing

To verify legacy starters are disabled:

```bash
# Run with heartbeat (default) - should see "Skipping legacy..." messages
python manage.py run_heartbeat

# Run with legacy mode - should see normal startup messages
export THOR_SCHEDULER_MODE=legacy
python manage.py runserver
```

## Notes

- **MarketGrader** service is NOT a heartbeat job (not part of this refactor) and continues to start/stop normally
- **MarketOpenCapture** supervisor is NOT disabled (not part of legacy multi-supervisor landscape)
- **Schwab Poller** supervisor is NOT disabled (separate from market-tick-driven work)
- All log messages clearly indicate which mode disabled what, for easy debugging

---

**Last Updated**: 2025-01-11
**Status**: ✅ Complete - All legacy starters guarded with THOR_SCHEDULER_MODE checks
