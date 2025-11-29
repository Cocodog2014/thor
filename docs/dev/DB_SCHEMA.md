# Database Schema (Human-Readable)

Summaries of Django models and important fields.

MarketSession (key fields):
- Identification: `session_number`, `capture_group`
- Local calendar: `year`, `month`, `date`, `day`, `captured_at`
- Market: `country`, `future`, `bhs`, `weight`, `wndw`
- Open snapshot prices: `last_price`, `bid_price`, `ask_price`, `spread`, sizes, `volume`
- Targets: `entry_price`, `target_high`, `target_low`, `target_hit_*`
- 24h stats: `prev_close_24h`, `open_price_24h`, diffs, range
- 52w stats: low/high, range, pct fields
- Outcome metrics: strong/buy/sell counts + percentages
- Unique: `(country, year, month, date, future)`

GlobalMarkets.Market (outline):
- `country`, `timezone_name`, `is_control_market`, enable flags
- Local schedule (open/close times), weights

Rolling52WeekStats (outline):
- `symbol`, `high_52w`, `low_52w`, dates, `last_price_checked`

Keep this doc synchronized with migrations.
