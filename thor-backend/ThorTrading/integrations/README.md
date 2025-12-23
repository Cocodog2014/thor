# ThorTrading Integrations

This folder contains all external system integrations that
**drive or influence ThorTrading behavior**.

ThorTrading itself does not own market timing or session boundaries.
Those responsibilities live outside the app and are integrated here.

---

## Current Integrations

### GlobalMarkets

GlobalMarkets is the **single source of truth** for:

- Market open / close
- Session boundaries
- Market status (OPEN / CLOSED)

ThorTrading reacts to GlobalMarkets signals to:

- Capture market-open snapshots
- Start and stop background workers
- Finalize market-close metrics

ThorTrading never computes its own session timing.

📄 See: `globalmarkets.md`
