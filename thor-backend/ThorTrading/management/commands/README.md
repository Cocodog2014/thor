# Management Commands Cheat Sheet

Four high-safety commands and their flags. Run from `A:\Thor\thor-backend` with `python manage.py <command>`.

## backfill_capture_group
- Deprecated: MarketSession grouping uses `session_number` now; command is a no-op.

## backfill_feed_symbols
- Purpose: fill missing `feed_symbol` from leading-slash `symbol` values; normalize symbol when safe.
- Safety: no global transaction; conflict check before symbol update.
- Flags:
  - `--dry-run` (no writes)
  - `--batch-size` (default 1000)
  - `--verbose`

## link_intraday_twentyfour
- Purpose: link `MarketIntraday.twentyfour` to existing `MarketTrading24Hour` parents.
- Safety: does **not** create parents unless asked.
- Flags:
  - `--batch-size` (default 500)
  - `--max-rows` (optional cap)
  - `--dry-run` (no writes)
  - `--create-missing` (allow parent creation; otherwise skips)
  - `--verbose`

## purge_market_sessions
- Purpose: delete **all** `MarketSession` rows.
- Safety: double confirmation required.
- Flags:
  - `--dry-run` (no writes; shows count)
  - `--yes-i-am-sure`
  - `--confirm DELETE`
