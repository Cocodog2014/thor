# GlobalMarkets

GlobalMarkets holds market metadata, trading-day gates, and status helpers consumed by other apps. Highlights:

- `models/` — Market model (timezone, trading_hours, trading_days) and trading calendar.
- `services/market_clock.py` — Computes local market time, trading-day gating, and status payloads.
- `views/` / `urls.py` — API surface for markets and calendar.
- `management/` — One-off reconcile/debug commands (no schedulers).
- `signals.py` — Emits status updates for downstream listeners.

Admin: Markets use a checkbox form for `trading_days`; blank tracks all days. No futures-specific logic remains.
