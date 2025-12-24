# ThorTrading Models

All persistent data models for the trading stack live here. The app is now instrument-neutral: fields use `symbol` (not `future`) and are keyed by `country + symbol` to stay consistent across sessions, intraday bars, and 24h rolls.

---

## Core Models

- MarketSession  
  One row per instrument per market-open capture; keyed by `capture_group + symbol` and `country`. Stores signals, targets, market-open stats, close/range metrics, session volume, and historical window counts (via `country_symbol_wndw_total` / `country_symbol`).

- MarketIntraday  
  1-minute OHLCV bars per `country + symbol` (using `CONTROL_COUNTRY_CHOICES`); uniqueness constraint on timestamp/country/symbol plus supporting indexes; optional link to the 24h roll.

- MarketTrading24Hour  
  Rolling 24h JP→US session aggregates per `capture_group + country + symbol` (unique together) with an index on `session_date/country/symbol`.

- VwapMinute  
  Per-minute raw snapshots (last + cumulative volume) for VWAP pipelines.

- Rolling52WeekStats  
  Rolling 52w extremes (and optional all-time extremes) per **symbol** (global, not country-scoped) with a batch update helper.

- TargetHighLowConfig  
  Per-instrument target configuration (points/percent/disabled) aligned to `country + symbol`.

- RTD Models (rtd.py)  
  Instrument catalog (`TradingInstrument`, categories, signal weights/stats, contract weights) shared across services.

---

## Design Notes

- Instrument-neutral: every model uses `symbol`; legacy `future` fields were renamed.
- Country-scoped analytics: composite keys are `country + symbol` (plus time where relevant).
- Session-centric: append-only where feasible; captures and metrics reference `capture_group` for grouping events.
- Indexes & constraints: enforced uniqueness per time bucket and country/symbol to keep data clean and queryable.
