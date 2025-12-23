# ThorTrading

ThorTrading is the real-time futures analytics and intraday metrics engine
for the Thor platform.

It ingests live market data, captures market-open snapshots, computes
intraday and session-level metrics, grades trades, and exposes results
through APIs and admin tools.

This README is a **high-level orientation only**.
Detailed behavior is documented inside each subsystem folder.

---

## What ThorTrading Owns

- Futures quote enrichment (YM, ES, NQ, RTY, CL, GC, etc.)
- Market-open session capture
- Intraday OHLCV bars & VWAP
- Trade grading (targets / stops)
- 24-hour & 52-week metrics
- Backend APIs for dashboards
- Admin inspection tools

---

## What ThorTrading Does NOT Own

- Market open / close times
- Session boundaries
- Frontend timers

Those are owned by **GlobalMarkets**.

---

## How to Read the Docs

Start here:

📄 `docs/README.md`

Then read the full runtime flow:

📄 `docs/FLOW.md`

Then dive into subsystems as needed.

---

## Subsystem Documentation

- Models → `models/README.md`
- Services & workers → `services/README.md`
- APIs → `api/README.md`
- Realtime heartbeat → `realtime/README.md`
- GlobalMarkets integration → `globalmarkets/README.md`
