# ThorTrading Runtime Flow

This document explains how data moves through ThorTrading at runtime.

---

## High-Level Flow

Live Quotes (Redis)
→ Quote Enrichment
→ Market-Open Capture
→ Intraday / VWAP / 52-Week Workers
→ Trade Grading
→ Database
→ APIs
→ Frontend

---

## Ownership Rules

- GlobalMarkets decides WHEN markets open/close
- ThorTrading reacts to those events
- ThorTrading never computes its own session boundaries

---

## Worker Lifecycle

- Workers start when GlobalMarkets emits market_opened
- Workers stop when market_closed fires
- No free-running loops detached from market state

---

## Frontend Interaction

- Frontend polls ThorTrading APIs
- Poll cadence is driven by a shared Global Timer
- No local frontend timers
