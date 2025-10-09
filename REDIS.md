# ⚡ Redis Setup for Thor (Windows 11 + Docker Desktop)

This guide sets up a local Redis instance for the live data pipeline using Docker Desktop on Windows 11.

## Why Redis?
- Low latency live bus for quotes
- Streams for durable, replayable ingestion
- Hashes for instant latest snapshot per symbol

## Prerequisites
- Windows 11
- Docker Desktop installed and running

## Start Redis

In the project root (`A:\\Thor`):

```powershell
# Start Redis in Docker
docker compose up -d redis

# Check status
docker compose ps

# Tail logs (optional)
docker compose logs -f redis
```

The service is defined in `docker-compose.yml` and exposes port `6379`.

## Health Check (optional)

```powershell
# Expect PONG
docker exec thor_redis redis-cli ping
```

## Data Persistence
- Redis persists under `./docker/redis/data` (mapped to `/data` in the container)
- AOF is enabled, snapshots every 60s if 1000 changes

## Environment variable

Set the URL for the backend and scripts:

```powershell
$env:REDIS_URL = 'redis://localhost:6379/0'
```

Optionally add to `.env` for Django.

## Test Connectivity from Python

First install dependencies (only once):

```powershell
cd A:\Thor\thor-backend
pip install -r requirements.txt
```

Then run the test script:

```powershell
# With the backend venv activated
python .\scripts\test_redis.py
```

Expected output:
- Connecting to redis://localhost:6379/0
- PING -> True
- SET/GET -> ok

## Next Steps
- Implement Redis Streams and latest-hash writers in collectors (xlwings and Schwab)
- Add Django endpoints `/api/quotes` (snapshot) and `/api/quotes/stream` (SSE)
- Add Postgres ingestor worker that tails Streams and batches inserts
