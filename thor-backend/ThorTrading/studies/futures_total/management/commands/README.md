# Futures Total Management Commands

This folder contains the *canonical* Django `Command` classes for the Futures Total study.

Important:
- Django discovers commands under `ThorTrading.management.commands`.
- The modules there are intentionally tiny shims that import `Command` from this folder.
- Command business logic lives under `ThorTrading.studies.futures_total.command_logic`.

See also: `ThorTrading/studies/futures_total/management/README.md`.

---

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

## purge_market_sessions
- Purpose: delete **all** `MarketSession` rows.
- Safety: double confirmation required.
- Flags:
  - `--dry-run` (no writes; shows count)
  - `--yes-i-am-sure`
  - `--confirm DELETE`
