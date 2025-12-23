# Thor Realtime Flow

## Entrypoints
- Heartbeat jobs: ThorTrading/realtime/jobs/* (registered via ThorTrading.realtime.provider)
- GlobalMarkets signals: ThorTrading/integrations/globalmarkets_hooks.py
- HTTP endpoints: ThorTrading/api/* (aliases of ThorTrading.views)

## Heartbeat jobs (reads → writes)
- intraday_tick: LiveData quotes → intraday supervisor step → bar queues/DB
- closed_bars_flush: bar queues → MarketIntraDay (DB)
- market_metrics: enriched quotes → MarketHighMetric updates
- market_grader: grading pass over pending sessions
- week52_extremes: quotes → Rolling52WeekStats
- vwap_minute_capture: LiveData minute snapshot → VwapMinute rows
- twentyfour_hour: enriched quotes → 24h stats per country
- preopen_backtest: pre-open window → backtest stats per future

## Signal flows
- Market open/close: GlobalMarkets signals → capture services → intraday supervisor

## Redis keys (examples)
- LiveData snapshots (per country/symbol)
- Bar queues (per market/country key; avoid "Futures" key)

## DB tables touched (examples)
- MarketSession, MarketIntraDay, VwapMinute, Rolling52WeekStats, metrics/grader outputs
