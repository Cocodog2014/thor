# GlobalMarkets (World Clock)

Single source of truth for market schedules, local time, and open/close status.

What it controls:
- Control markets (Tokyo, Shanghai, Bombay, Frankfurt, London, Pre_USA, USA, Toronto, Mexico)
- Localized date/time (`get_current_market_time()`)
- Status transitions: `CLOSED → OPEN → CLOSED` via MarketMonitor
- Next open/close scheduling; holiday/disabled flags

Consuming services:
- Market Open capture (sessions)
- IntradayMarketSupervisor
- 52-Week monitor

See `SEED_DATA.md` for canonical schedules and weights.
