# Thor Web Stack Guide

This note captures how the Docker-based "production" stack is wired so you can reason about real-time data refresh, background jobs, and troubleshooting.

## Core Services

| Service | Container | Purpose | Key Command |
| --- | --- | --- | --- |
| `thor_web` | `web` | Gunicorn + Django API/GQL server exposed on host `8001`. | `docker compose logs -f web` |
| `thor_worker` | `worker` | Runs `python manage.py run_thor_stack` which launches every background supervisor (intraday bars, VWAP, Excel bridge retries, etc.). | `docker compose logs -f worker` |
| `thor_postgres` | `postgres` | Postgres 15 storing ThorTrading_* tables and account data. | `docker compose exec postgres psql -U thor_user -d thor_db` |
| `thor_redis` | `redis` | Redis 7 for quotes stream + rolling VWAP caches. Mapped to host `localhost:6379`. | `docker compose exec redis redis-cli` |

Both app containers share the same image (`./thor-backend/Dockerfile`) and `.env`. Differences come from service-level overrides.

## Environment Contracts

- `.env` remains the single source of truth for secrets. Compose overrides only connection targets:
  - `DB_HOST=postgres`, `REDIS_HOST=redis`, `REDIS_URL=redis://redis:6379/0` inside Docker.
  - `THOR_STACK_AUTO_START=0` on `thor_web` so Gunicorn does not start any background loops.
  - `THOR_STACK_AUTO_START=1` on `thor_worker` so the stack boots exactly once.
- If you run the legacy Excel/xlwings poller on the host, export `REDIS_URL=redis://localhost:6379/0` before starting it so that it hits the Compose Redis instance.

## Lifecycle

1. **Build/Start**
   ```powershell
   cd A:\Thor
   docker compose up -d --build web worker
   ```
2. **Watch logs**
   ```powershell
   docker compose logs -f worker    # intraday + supervisors
   docker compose logs -f web       # API only
   ```
3. **Inspect health**
   - Gunicorn: `curl http://localhost:8001/api/health` (or hit any Django endpoint).
   - Worker: look for `Intraday ...` lines every ~10s; absence means the supervisor loop stalled.

## Data Flow At A Glance

```
Excel/xlwings (host) ──writes quotes──> thor_redis ──> thor_worker
                                             │             │
                                             │             ├─ updates MarketIntraday + VWAP tables
                                             │             └─ publishes rolling VWAP payloads back into Redis
                                             └─> thor_web reads hashes/streams + Postgres for chart APIs
```

- `api.redis_client.get_redis()` respects `settings.REDIS_URL`, so once the host poller writes to `thor_redis`, the `/api/quotes*` endpoints will see the same payloads as dev.
- Intraday APIs (charts, VWAP) pull from Postgres tables (`ThorTrading_marketintraday`, `ThorTrading_vwapminute`) that the worker refreshes.

## Verification Checklist

1. **Redis data available**
   ```powershell
   docker compose exec web python manage.py shell -c "from api.redis_client import get_redis, latest_key; r=get_redis(); print(r.hgetall(latest_key('YM')))"
   ```
   Expect non-empty hashes once the Excel poller is pointed at `localhost:6379`.

2. **Intraday table advancing**
   ```powershell
   docker compose exec postgres psql -U thor_user -d thor_db -c "SELECT future, MAX(timestamp_minute) FROM \"ThorTrading_marketintraday\" GROUP BY future ORDER BY future;"
   ```
   Rows should tick each minute when the worker is healthy.

3. **API parity check**
   ```powershell
   curl "http://localhost:8001/api/quotes?symbols=YM,ES"
   curl "http://localhost:8001/api/session?market=USA&future=YM"
   ```
   Compare to `http://localhost:8000/...` (dev runserver). Differences usually signal Redis or worker misconfiguration.

## Troubleshooting

| Symptom | Checks |
| --- | --- |
| Timestamp updates but chart data frozen | Run the Postgres query above; if `MAX(timestamp_minute)` is stale, the worker is either down or writing to another DB. Restart worker (`docker compose restart worker`) and inspect logs for exceptions. |
| `/api/quotes` empty | From inside `thor_web`, `r.keys('quotes:latest*')`. If empty, ensure the Excel poller writes to `redis://localhost:6379/0` and that `thor_redis` container is running. |
| Worker log spam `xlwings not available` | Expected inside Linux container; Excel poller remains host-side. Silence by setting `DATA_PROVIDER` accordingly or ignore if Postgres/Redis updates continue. |
| API container launching supervisors | Confirm `THOR_STACK_AUTO_START=0` via `docker compose exec web env | findstr THOR_STACK`. If missing, rebuild/compose down/up. |
| Redis mismatch between dev and Docker | Remember host dev uses native Redis (127.0.0.1). When testing Compose you must target `localhost:6379` (host port) for any producers outside Docker.

## Handy Commands
# Thor Web Overview

This document summarizes what the Thor Web stack is, how it runs, and the helper pieces we added today. Use it as the top-level reference that other backend docs can point to.

## What Thor Web Does

- Hosts the Django/Gunicorn API on port `8001` (`thor_web` service in `docker-compose.yml`).
- Connects to the shared Postgres + Redis services so the frontend can read intraday charts, VWAP values, and Schwab account data.
- Exposes the same codebase used in development; the only difference is that it runs inside Docker with production-like settings.

## How It Works

1. **Image & Config** – Both `thor_web` and `thor_worker` use `thor-backend/Dockerfile` and the shared `.env`. Compose overrides set `DB_HOST=postgres`, `REDIS_HOST=redis`, and `REDIS_URL=redis://redis:6379/0` so containers talk over the internal network.
2. **API Container (`thor_web`)** – Runs `gunicorn thor_project.wsgi:application …` and now sets `THOR_STACK_AUTO_START=0`. That flag keeps the app from launching background threads so the container stays lightweight.
3. **Worker Container (`thor_worker`)** – Runs `python manage.py run_thor_stack`. The new management command forces the Thor background stack (intraday supervisor, market metrics, etc.) to start independently of Gunicorn and keeps it alive with a simple sleep loop.
4. **Data Helpers** – Redis is still fed by the Excel/xlwings job on the host. Point that job at `redis://localhost:6379/0` so its writes land in the Compose Redis instance that both containers share. Once data is in Redis, the worker pushes it into Postgres and the API reads it back out.

## Morning Helper Summary

- **`run_thor_stack` command** – Dedicated entry point for all supervisors. Lets us run the stack anywhere (local host or Docker worker) without relying on Django startup side effects.
- **`ThorTrading/services/stack_start.py`** – Hosts `start_thor_background_stack`, the coordinator that spins up the Excel poller supervisor, intraday supervisor, market graders, etc. We added a `force` flag so the worker can bypass Django’s autoreload guards.
- **`THOR_STACK_AUTO_START` env flag** (handled in `ThorTrading/apps.py`) – When set to `0`, the app skips calling `start_thor_background_stack`. This keeps the web container lightweight while allowing the worker to run the full stack by leaving the flag enabled.
- **`thor_worker` service** – New docker-compose entry that runs `python manage.py run_thor_stack --keepalive 15`, depends on Postgres/Redis health, and is the only place the supervisors run in Docker.

## Flow Diagram

```
┌────────────────┐         docker compose        ┌────────────────┐
│  thor_worker   │  runs  python manage.py  ───▶ │ run_thor_stack │
│  (worker svc)  │──────── run_thor_stack ───┐   │  command       │
└────────────────┘                            │   └─────┬─────────┘
                       │         │ force=True
                       │         ▼
┌────────────────┐       imports / calls    ┌───────────────┐
│ ThorTrading/   │◀──── start_thor_stack ◀──│ stack_start.py│
│ apps.py        │       (if auto-start)    │ start_thor_   │
│ (THOR_STACK_   │                          │ background... │
│ AUTO_START flag│                          └─────┬─────────┘
└────────────────┘                                │ spawns supervisors
                      │ (Excel poller, intraday,
                      │  VWAP, graders, etc.)
                      ▼
                   background threads running
                   within the worker container
```

Legend:

- `thor_worker` is the docker-compose service keeping the worker container alive.
- `run_thor_stack` is the Django management command executed inside that container.
- `stack_start.py` holds `start_thor_background_stack`, which the command calls with `force=True` to bypass autoreload guards and launch all supervisors.
- `ThorTrading/apps.py` only auto-starts the stack when `THOR_STACK_AUTO_START` is not set to `0`; in Docker we disable it for `thor_web` and leave it enabled for the worker.

## When to Reference This File


For deeper topics—database schemas, Excel ingestion, frontend wiring—create separate Markdown files that can cite this overview instead of duplicating it.
