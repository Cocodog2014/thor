# GlobalMarkets Integration

This document describes how ThorTrading integrates with GlobalMarkets.

---

## Ownership Model

GlobalMarkets owns:
- Market schedules
- Open / close decisions
- Session boundaries

ThorTrading owns:
- Data capture
- Metrics
- Trade grading
- APIs

---

## Signal Flow

GlobalMarkets emits:
- market_opened
- market_closed

ThorTrading responds by:
- Capturing market-open sessions
- Starting or stopping workers
- Finalizing close metrics

---

## Design Rules

- No duplicate timers
- No independent market clocks
- No free-running workers
