ThorTrading/
  services/
    metrics/                     ← NEW consolidated metrics package
    │
    ├── __init__.py              # Public entry point: re-exports everything
    │
    ├── row_metrics.py           # Per-quote calculations for /api/quotes/latest
    │   ├─ compute_row_metrics()         ← math for diff/pct/spread/52w deltas
    │   ├─ _diff(), _pct(), _to_float()  ← low-level helpers
    │
    ├── session_open.py          # Metrics executed at market OPEN
    │   ├─ MarketOpenMetric
    │       ├─ Sets market_open = last_price
    │       ├─ Initializes market_high_open & market_low_open
    │
    ├── session_high_low.py      # Intraday rolling HIGH/LOW tracking
    │   ├─ MarketHighMetric
    │       ├─ Updates market_high_open
    │       ├─ Computes market_high_pct_open
    │   ├─ MarketLowMetric
    │       ├─ Updates market_low_open
    │       ├─ Computes market_low_pct_open
    │
    ├── session_close_range.py   # Metrics executed when a market CLOSES
    │   ├─ MarketCloseMetric
    │       ├─ last_price → market_close
    │       ├─ market_high_pct_close
    │       ├─ market_low_pct_close
    │       ├─ market_close_vs_open_pct
    │   ├─ MarketRangeMetric
    │       ├─ market_range = high - low
    │       ├─ market_range_pct = (range / open) * 100
    │
    └── (legacy removed)
      (previous single-file implementations deleted: market_metrics.py, metrics.py)


Other Services Referencing Metrics
----------------------------------
services/quotes.py                → uses compute_row_metrics()
services/MarketOpenCapture.py     → uses MarketOpenMetric + stats inject
services/intraday supervisors     → will call MarketHigh/Low/Close/Range


