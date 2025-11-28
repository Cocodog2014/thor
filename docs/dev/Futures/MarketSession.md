# MarketSession – Data Dictionary

Each row in `FutureTrading_MarketSession` represents **one future at one market open session**.

## Identification / Time

| Column                    | Type        | Description |
|---------------------------|------------|-------------|
| `id`                      | int (PK)   | Auto-increment primary key. |
| `session_number`          | int        | Sequential session ID (1, 2, 3, …) across all days. |
| `capture_group`           | int        | Group identifier for rows captured in the same market-open batch. |
| `year`                    | int        | Calendar year of the capture (YYYY). |
| `month`                   | int        | Calendar month (1–12). |
| `date`                    | int        | Calendar day of month (1–31). |
| `day`                     | varchar    | Day name (e.g. `Mon`, `Tue`). |
| `captured_at`             | datetime   | Exact timestamp (timezone-aware) when this snapshot was taken. |

## Instrument Info

| Column                    | Type        | Description |
|---------------------------|------------|-------------|
| `country`                 | varchar    | Country / market (e.g. `USA`, `Germany`). |
| `future`                  | varchar    | Symbol code (e.g. `ES`, `NQ`, `YM`, `TOTAL`). |
| `country_future`          | decimal    | Numeric ordering aid that keeps countries/futures grouped together. |
| `weight`                  | int        | Weight assigned to the row (primarily for TOTAL compositions). |
| `bhs`                     | varchar    | Signal at capture (`STRONG_BUY`, `BUY`, `HOLD`, `SELL`, `STRONG_SELL`). |
| `wndw`                    | varchar    | Optional outcome label (`WORKED`, `DIDNT_WORK`, `NEUTRAL`, `PENDING`). |
| `country_future_wndw_total` | bigint  | Historical count backing the `wndw` classification. |

## Order Book / Trade Snapshot

| Column            | Type      | Description |
|-------------------|-----------|-------------|
| `bid_price`       | decimal   | Best bid at capture. |
| `bid_size`        | int       | Size at best bid. |
| `ask_price`       | decimal   | Best ask at capture. |
| `ask_size`        | int       | Size at best ask. |
| `last_price`      | decimal   | Last traded price at capture. |
| `spread`          | decimal   | `ask_price - bid_price`. |
| `entry_price`     | decimal   | Price we assume as entry for backtest logic. |

## Target / Backtest Hit Info

| Column            | Type      | Description |
|-------------------|-----------|-------------|
| `target_hit_price`| decimal   | First price where target was hit. |
| `target_hit_type` | varchar   | `TARGET` (profit) or `STOP` depending on which level hit first. |
| `target_high`     | decimal   | Calculated upside target price from entry. |
| `target_low`      | decimal   | Calculated downside / stop price from entry. |
| `target_hit_at`   | datetime  | When the target/stop was first hit. |

## Volume / VWAP

| Column        | Type      | Description |
|---------------|-----------|-------------|
| `volume`      | bigint    | Volume at capture or for the session window (confirm usage). |
| `vwap`        | decimal   | Volume Weighted Average Price over the lookback window. |

## Intraday Market Metrics (current session)

| Column                     | Type      | Description |
|----------------------------|-----------|-------------|
| `market_open`              | decimal   | Price at the official market open for this session. |
| `market_high_open`         | decimal   | Highest price seen *since open* at capture time. |
| `market_high_pct_open` | decimal   | `% move from market open up to the intraday high (stored when a new high is set)`. |
| `market_low_open`          | decimal   | Lowest price seen *since open* at capture time. |
| `market_low_pct_open`      | decimal   | `% change from open to market_low_open`. |
| `market_close`             | decimal   | Latest price considered “close” for this session (at end of session). |
| `market_high_pct_close`    | decimal   | `% change from close up to session high`. |
| `market_low_pct_close`     | decimal   | `% change from close down to session low`. |
| `market_close_vs_open_pct` | decimal | `% change from market_open to market_close`. |
| `market_range`             | decimal   | `session_high - session_low` for this session. |
| `market_range_pct`         | decimal   | `market_range / market_open` (range as % of open). |

## 24-Hour Metrics

| Column               | Type      | Description |
|----------------------|-----------|-------------|
| `prev_close_24h`     | decimal   | Previous 24-hour session close. |
| `open_price_24h`     | decimal   | Current 24-hour open price. |
| `open_prev_diff_24h` | decimal   | `open_price_24h - prev_close_24h`. |
| `open_prev_pct_24h`  | decimal   | `% change between `open_price_24h` and `prev_close_24h`. |
| `low_24h`            | decimal   | Lowest price in rolling 24h window. |
| `high_24h`           | decimal   | Highest price in rolling 24h window. |
| `range_diff_24h`     | decimal   | `high_24h - low_24h`. |
| `range_pct_24h`      | decimal   | `range_diff_24h / open_price_24h`. |

## 52-Week Metrics

| Column          | Type      | Description |
|-----------------|-----------|-------------|
| `low_52w`       | decimal   | 52-week low price. |
| `low_pct_52w`   | decimal   | `% move from 52w low to current price`. |
| `high_52w`      | decimal   | 52-week high price. |
| `high_pct_52w`  | decimal   | `% move from 52w high to current price`. |
| `range_52w`     | decimal   | `high_52w - low_52w`. |
| `range_pct_52w` | decimal   | `range_52w / low_52w` (or other chosen baseline – document exact formula). |

## Composite / Grader Stats

| Column                    | Type      | Description |
|---------------------------|-----------|-------------|
| `weighted_average`        | decimal   | Weighted average score across instruments for this session. |
| `instrument_count`        | int       | Number of instruments included in the composite. |

## Backtest Outcome Counters

Each “worked” means the signal hit its profit target before the stop. “didnt_work” means stop hit first or other failure condition.

| Column                               | Type | Description |
|--------------------------------------|------|-------------|
| `strong_buy_worked`                  | int  | Count of **strong buy** signals that worked. |
| `strong_buy_worked_percentage`       | decimal | `strong_buy_worked / total_strong_buy`. |
| `strong_buy_didnt_work`             | int  | Count of strong buys that failed. |
| `strong_buy_didnt_work_percentage`  | decimal | Failure rate for strong buys. |
| `buy_worked`                         | int  | Count of **buy** signals that worked. |
| `buy_worked_percentage`             | decimal | Success rate for buys. |
| `buy_didnt_work`                    | int  | Buys that failed. |
| `buy_didnt_work_percentage`         | decimal | Failure rate for buys. |
| `hold`                               | int  | Holds (no trade / neutral). |
| `strong_sell_worked`                | int  | Strong sell signals that worked. |
| `strong_sell_worked_percentage`     | decimal | Success rate for strong sells. |
| `strong_sell_didnt_work`           | int  | Strong sells that failed. |
| `strong_sell_didnt_work_percentage` | decimal | Failure rate for strong sells. |
| `sell_worked`                       | int  | Sell signals that worked. |
| `sell_worked_percentage`           | decimal | Success rate for sells. |
| `sell_didnt_work`                  | int  | Sells that failed. |
| `sell_didnt_work_percentage`       | decimal | Failure rate for sells. |
