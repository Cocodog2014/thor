# Stock Trading Layout & Roadmap

## Frontend Layout
- Full-width Stock Trading route renders two-column grid with Account panel (left) and Positions panel (right).
- `Account` component consumes mode-aware blueprint (`live`, `paper`) from `Account/accountData.ts` to drive ordering and labeling.
- `Positions` panel groups rows by brokerage account, mirrors mobile reference (symbol rows, subtotals, overall totals) and supports expandable account headers.
- Global drawer remains accessible; optional secondary drawer overlays right edge for contextual tools.
- Mode toggle (live vs paper) persists in page state and flows into Account metrics.

- Slash layout confirmed in latest reference screenshot—mirror structure exactly.
## Positions Panel Spec
- **Column Order**: `Symbol`, `P/L Day`, `Market Change`, 'Mark', `Trade Price`, `P/L Open`, `P/L %`, `P/L YTD`, `Margin`, `Delta`, `Ask`, `Bid` (exact order locked per request).
- **Column Header Bar**: Cooperates with horizontal scroll container; sticky header includes dropdowns for P/L basis (Day/Open/YTD) and price source (Last/Mark/Ask/Bid) affecting the relevant columns.
- **Horizontal Scrolling**: Table body sits inside overflow-x container so additional greek/quote columns remain accessible on smaller breakpoints while header stays fixed.
- **Account Group**: Displays account name, aggregate P/L numbers, and caret for collapse; rows show symbol, size change indicator, and values matching column order; support for conditional formatting on gains/losses.
- **Subtotals & Overall Totals**: Each account ends with `Subtotals` row summing numeric columns; after all accounts, render `Overall Totals` row for aggregated positions.
- **Footer Metrics**: Below table, display stacked summary rows in order: `P/L Day`, `P/L Open`, `Net Liq`, `Available Dollars`, `Position Equity` (all reflect overall totals). Values gain/loss color-coded; labels remain neutral.
- **Color Treatment**: Gains in green, losses in red, neutral in light gray to mirror reference screenshots while ensuring accessibility contrast.

## Upcoming Frontend Enhancements
- Flesh out Positions panel interactions (collapse per account, hover tooltips, position filtering) and add toggleable columns (Delta, Bid/Ask, Margin).
- Introduce performance tiles (daily change, YTD) and recent orders feed beneath primary grid.
- Wire drawer tabs for orders/history views and align styling with main layout tokens.
- Stand up `WatchList` container (mirrors panel styling) for quote summaries; ensure doc stays updated with column/interaction changes.

## Watch List Panel Spec
- **Column Order**: `Symbol`, `Last`, `Change`, `P/L %`, `Mark`, `Volume` (extend as needed for greeks or alerts).
- **Row Composition**: Symbol column includes primary ticker plus smaller descriptor line; values right-align and inherit same typography scale as header.
- **Styling Parity**: Shares panel chrome with Account/Positions (blurred glass, border, header stack) to maintain dashboard cohesion.
- **Data Source**: Placeholder data mocked in `WatchList.tsx`; replace with live quote feed once backend wiring completes.

## Backend Integration Plan
- Expose REST endpoints for balances, positions, orders segregated by trading mode.
- Add provider abstraction to swap between live (Schwab API) and paper (simulated) data sources.
- Persist periodic snapshots for trend charts; secure mutating routes with mode-aware guards.

## Data Fields Surfaced (Account Panel)
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
- Determine any additional balances required (SMA, cash available for withdrawal, etc.).
- Decide authentication path for brokerage integration (Schwab API, Excel bridge, other).
