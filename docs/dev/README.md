# Thor Developer Docs Index

Purpose: Central, scannable index of focused developer documentation. Each document is narrowly scoped so you can quickly find authoritative details.

- ARCHITECTURE.md: High-level system components, data flow, and boundaries.
- GLOBALMARKETS.md: Markets, timing authority, timezones, and capture schedules.
- FUTURETRADING.md: Futures capture pipeline, MarketOpen, targets, and metrics.
- DATA_CONTRACTS.md: Canonical JSON payloads and fixtures used across services.
- DB_SCHEMA.md: Tables and relationships (Postgres), including MarketSession.
- ENV_VARS.md: Required and optional environment variables with defaults.
- METRICS_MONITORS.md: Operational metrics, alerts, and health checks.
- SEED_DATA.md: Seed strategy, files (`thor-backend/data`), and commands.
- DEVELOPMENT.md: Day-to-day workflows, testing, migrations, and troubleshooting.

Quick Start

1. Seed baseline config:
   - `Push-Location A:\Thor\thor-backend; python manage.py thor_seed_all --data-dir "A:\\Thor\\thor-backend\\data"; Pop-Location`
2. Market open capture overview:
   - See `FUTURETRADING.md` and `GLOBALMARKETS.md` for timing and session grouping.
3. Data contracts and fixtures:
   - See `DATA_CONTRACTS.md` and `SEED_DATA.md` for canonical examples.
