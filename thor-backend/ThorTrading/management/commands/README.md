# Management Commands

These are Django-discoverable `manage.py` commands for ThorTrading.

Command business logic lives under `ThorTrading/studies/futures_total/command_logic`.

---

# Management Commands Cheat Sheet

Run from `A:\\Thor\\thor-backend` with `python manage.py <command>`.

## purge_market_sessions
- Purpose: delete **all** `MarketSession` rows.
- Safety: double confirmation required.
- Flags:
	- `--dry-run` (no writes; shows count)
	- `--yes-i-am-sure`
	- `--confirm DELETE`
