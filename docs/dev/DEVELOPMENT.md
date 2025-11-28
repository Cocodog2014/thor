# Thor Dev Overview

This overview points to focused docs under `docs/dev/` for deep dives. GlobalMarkets is the single timing authority. See `GLOBALMARKETS.md` and `SEED_DATA.md` for canonical schedules and constants.

- Architecture: `ARCHITECTURE.md`
- GlobalMarkets (world clock + schedules): `GLOBALMARKETS.md`
- FutureTrading (sessions, capture, metrics): `FUTURETRADING.md`
- Data Contracts (Redis schemas + API payloads): `DATA_CONTRACTS.md`
- DB Schema (model/field tables): `DB_SCHEMA.md`
- Environment Variables: `ENV_VARS.md`
- Monitors & Metrics (intraday, 52w, VWAP): `METRICS_MONITORS.md`
- Canonical Seed Data: `SEED_DATA.md`

## Database Recovery (Crash/Rebuild)

- Goal: Recreate a clean Postgres, run migrations, and reseed authoritative config.

### Steps (PowerShell)

- Stop apps/services that use the DB:
	- If using Docker: `Push-Location A:\Thor; docker-compose down; Pop-Location`
	- If running Django locally: stop any `runserver` processes.

- Reset Postgres data (Docker-based dev):
	- Remove the persisted volume/folder:
		- `Push-Location A:\Thor\docker\postgres\data; Remove-Item -Recurse -Force .\*; Pop-Location`
	- Start fresh containers:
		- `Push-Location A:\Thor; docker-compose up -d; Pop-Location`

- Apply migrations:
	- `Push-Location A:\Thor\thor-backend; python manage.py migrate; Pop-Location`

- Seed baseline configuration (markets, placeholders for futures/weights):
	- Recommended fixtures directory: `A:\Thor\thor-backend\data`
	- `Push-Location A:\Thor\thor-backend; python manage.py thor_seed_all --data-dir "A:\\Thor\\thor-backend\\data"; Pop-Location`

- Verify quick checklist:
	- `GlobalMarkets` entries exist (control markets enabled; correct timezones).
	- Django admin loads; no migration errors in logs.
	- Market open capture script runs without exceptions for at least one control market.

### Optional: Restore Historical Data

- If you maintain Postgres dumps, restore them before migrations/seed:
	- Example (Dockerized Postgres):
		- `Push-Location A:\Thor; docker-compose exec postgres bash -lc "psql -U postgres -d thor < /backups/thor_latest.sql"; Pop-Location`
	- Then re-run migrations if schema evolved.

### Notes

- `thor_seed_all` seeds canonical configuration only; it does not restore `MarketSession` history or Redis streams.
- Keep `docs/dev/SEED_DATA.md` in sync with fixture changes.
