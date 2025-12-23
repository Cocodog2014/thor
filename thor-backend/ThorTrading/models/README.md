# ThorTrading Models

This folder contains all persistent trading data models.

---

## Core Models

- MarketSession  
  One row per future per market open

- MarketIntraDay  
  1-minute OHLCV bars

- VwapMinute  
  Per-minute VWAP snapshots

- Rolling 24h & 52-week models  
  Long-range metrics

---

## Design Principles

- Session-centric design
- Country-scoped analytics
- Append-only where possible
