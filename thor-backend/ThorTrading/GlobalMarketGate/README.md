# GlobalMarketGate (ThorTrading)

## What this is
**GlobalMarketGate is the single door** between the **GlobalMarkets** app and **ThorTrading**.

GlobalMarkets decides market status (OPEN/CLOSED) and emits signals.
ThorTrading reacts by capturing sessions and running supervisors.

✅ One file, one place to debug: `global_market_gate.py`

---

## Dependencies
GlobalMarkets provides:
- `Market` model
- `market_opened` / `market_closed` signals

ThorTrading provides:
- `open_capture.capture_market_open(market)`
- `close_capture.capture_market_close(country)`
- `intraday_market_supervisor.on_market_open(market)`
- `intraday_market_supervisor.on_market_close(market)`
- optional grading service

---

## Environment variables

### Enable/disable the gate
- `THOR_USE_GLOBAL_MARKET_TIMER=1` (default)  
- `THOR_USE_GLOBAL_MARKET_TIMER=0` disables all signal handling

### Scheduler mode
- `THOR_SCHEDULER_MODE=heartbeat` (default)
  - heartbeat owns background jobs
  - gate does NOT start/stop the grading service
- `THOR_SCHEDULER_MODE=legacy`
  - gate will start grading on first open and stop on last close

---

## Startup / bootstrap
If your server restarts while markets are already OPEN, call:

- `bootstrap_open_markets()`

This will:
- find currently OPEN markets
- start intraday supervisors for those markets

Where to call it:
- typically inside `ThorTrading/apps.py` in `ready()` after signal receivers are imported.

---

## What to delete
If you previously had:
- `globalmarkets_hooks.py`

You should remove it once everything is merged into this gate file.

---

## Debugging tips
- Confirm GlobalMarkets is emitting `market_opened` / `market_closed`.
- Confirm the ThorTrading app imports `ThorTrading.GlobalMarketGate.global_market_gate`
  so the receivers register.
- Check logs for:
  - `GlobalMarketGate: detected <country> market OPEN`
  - `GlobalMarketGate: detected <country> market CLOSE`
