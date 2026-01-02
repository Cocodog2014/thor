# ThorTrading Services & Workers

This folder contains all background workers and services.

---

## Key Services

- MarketOpenCapture  
  Captures a snapshot at market open

- MarketGrader  
  Grades trades until resolved

- Intraday Supervisor  
  Maintains OHLCV bars

- VWAP Capture  
  Minute-based VWAP sampling

- 52-Week Supervisor  
  Rolling extremes monitoring

---

## Lifecycle

- Workers are started/stopped by GlobalMarkets signals
- No service owns its own notion of “market open”
