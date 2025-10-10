# Stock Trading Rebuild Notes

## Frontend Plan
- Build dedicated Stock Trading dashboard with live vs paper trading toggle (MVP prototype complete).
- Right-side drawer houses contextual tools (orders, positions, history).
- Compact balances panel mirrors brokerage screenshot; values currently hard-coded as placeholders.
- Next UI passes: add charts/tiles for performance, recent orders, and trade tickets.

## Backend Plan (Upcoming)
- Expose REST endpoints for account balances, orders, positions.
- Support dual environments (live vs paper) via provider abstraction.
- Persist snapshots for historical trending.
- Gate mutating operations behind trading mode safety checks.

## Data Fields to Surface
- Long Stock Value
- Maintenance Requirement
- Margin Balance
- Margin Equity
- Money Market Balance
- Net Liquidating Value
- Option Buying Power
- Settled Funds
- Short Balance
- Short Marginable Value
- Stock Buying Power
- Total Commissions & Fees YTD

## Open Questions
- Confirm data latency expectations for live vs paper feeds.
- Determine if additional balances (cash available for withdrawal, SMA, etc.) are required.
- Decide how to authenticate/brokerage integration (Schwab API, Excel pipe, others).
