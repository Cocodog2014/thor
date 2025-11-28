# Monitors & Metrics

Supervisors:
- IntradayMarketSupervisor: updates high/low, close/range on `OPEN`/`CLOSED`
- 52-Week Extremes: starts when any control market is `OPEN`
- VWAP minutes: capture + rolling windows

Key formulas:
- `market_high_pct_open = (high - open) / open * 100`
- `market_low_pct_open = (last - low) / low * 100`

Operational notes: intervals, logging, guard clauses, idempotency.
