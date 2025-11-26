# � Thor – Quick Start Guide

Simple startup sequence for Excel real-time data with Schwab integration.

---

## 1️⃣ Start Docker Services

```powershell
cd A:\Thor
docker compose up -d redis
docker compose up -d postgres
```

---

## 2️⃣ Start Cloudflare Tunnel

```powershell
Start-Service cloudflared
```

**Or manually** (in separate terminal):
```powershell
cd A:\Thor
cloudflared tunnel run thor
```

---

## 3️⃣ Activate Conda Environment & Start Django Backend

```powershell
cd A:\Thor\thor-backend
#conda activate Thor_inv

# Set environment variables for Excel Live data
$env:DATA_PROVIDER = 'excel_live'
$env:EXCEL_DATA_FILE = 'A:\\Thor\\RTD_TOS.xlsm'
$env:EXCEL_SHEET_NAME = 'LiveData'
$env:EXCEL_LIVE_RANGE = 'A1:N13'
$env:REDIS_URL = 'redis://localhost:6379/0'


# Start Django
#cd A:\Thor\thor-backend
python manage.py runserver
```

Note:
- The 52-week extremes monitor now auto-starts with the backend and updates `Rolling52WeekStats` from Redis in real time. To disable it, set `FUTURETRADING_ENABLE_52W_MONITOR=0` in Django settings or environment.

---

## 🔌 Connect to Postgres (psql)

Use these to open psql inside the running Docker container and list all tables.

```powershell
# From host, attach a shell into the DB container and run psql
docker exec -it thor_postgres psql -U thor_user -d thor_db

# In psql
\conninfo           -- show current connection
\dn                 -- list schemas
\dt *.*             -- list tables in all schemas
\dv *.*             -- list views in all schemas
\d "FutureTrading_marketsession"   -- describe a table (quoted name)
```

Alternative (using host psql without docker exec):

```powershell
# One‑off command (no interactive prompt)
$Env:PGPASSWORD = 'thor_password'
psql -h 127.0.0.1 -p 5432 -U thor_user -d thor_db -c "\dt *.*"
```

Notes:
- The default credentials come from `docker-compose.yml`: user `thor_user`, db `thor_db`, password `thor_password`.
- If you customized them in a `.env`, use those values instead.
- Seeing only a few tables? Ensure you’re connected to `thor_db` and run `\dt *.*` (across all schemas).

---

## 4️⃣ Start Excel Data Poller

Run this in a separate terminal to stream live TOS RTD data into Redis:

```powershell
cd A:\Thor\thor-backend
#conda activate Thor_inv

# Poll Excel every 3 seconds and publish to Redis
python manage.py poll_tos_excel

# Or customize the interval (in seconds)
python manage.py poll_tos_excel --interval 5
```

Notes:
- Runs until you press Ctrl+C
- Uses a Redis lock so only one Excel instance opens
- Frontend reads from Redis (no Excel opens from the UI)

### Data Flow (new)
- poll_tos_excel (producer) → reads Excel RTD and publishes quotes to Redis
- Backend API → serves quotes from Redis to the frontend
- Frontend → displays whatever is in Redis; no longer triggers Excel reads

---

## 5️⃣ Start Frontend

```powershell
cd A:\Thor\thor-frontend
npm run dev
```

## 6️⃣ (Optional) Start Frontend in Production (Preview)

Use this when serving the frontend through Cloudflare to avoid dev-module 404s.

```powershell
# In case the dev server is running on 5173, stop it first (close the terminal)

cd A:\Thor\thor-frontend

# 1) Build the production bundle
npm run build

# 2) Serve the built app on the SAME port Cloudflare expects (5173)
# Bind to IPv4 loopback to ensure Cloudflared can reach it
npx vite preview --host 127.0.0.1 --port 5173 --strictPort
```

Notes:
- Keep Django running on 8000 at the same time.
- Cloudflared is already configured so:
  - /, all other paths → http://127.0.0.1:5173 (this preview server)
  - /admin, /api, /static, /media → http://127.0.0.1:8000 (Django)
- Start order recommendation: Backend (8000) → Frontend preview (5173) → Cloudflared.

### Quick verify (optional)

```powershell
Invoke-WebRequest https://thor.360edu.org/ -UseBasicParsing
Invoke-WebRequest https://thor.360edu.org/api/ -UseBasicParsing
Invoke-WebRequest https://thor.360edu.org/admin/ -UseBasicParsing
```

---

## 📌 Important URLs

### Local Access
- **Backend API**: http://localhost:8000/api/
- **Admin Panel**: http://localhost:8000/admin/
  - Email: `admin@360edu.org`
  - Password: `Coco1464#`
- **Frontend**: http://localhost:5173

### Cloudflare Tunnel (Public HTTPS)
- **Frontend**: https://thor.360edu.org/
- **Admin Panel**: https://thor.360edu.org/admin/
- **Backend API**: https://thor.360edu.org/api/

### Schwab OAuth
- **Start OAuth**: https://thor.360edu.org/api/schwab/oauth/start/
- **Callback URL**: https://thor.360edu.org/schwab/callback


## 🔧 Troubleshooting
- ModuleNotFoundError: redis
  - You’re likely using the wrong Python (a local venv). Run `conda activate <your env>`; then `where python` should NOT point to `A:\Thor\thor-backend\venv`. Re-run `python -m pip install -r requirements.txt` inside that conda env.
- Postgres connection refused
  - Ensure the container is running: `docker ps`; confirm the mapped port (default host port 5432). If you used a different host port, set `DB_PORT` in `A:\Thor\thor-backend\.env`.
- Cloudflared is on at boot but you don’t want it running
  - In an elevated PowerShell: `Set-Service cloudflared -StartupType Manual; Stop-Service cloudflared`. See CloudFlare.md for the admin toggle and auto-recovery.

That's it! ⚡

## 🔒 Security Note: Consumer App Validation

**IMPORTANT**: The system now validates consumer apps to prevent fake registrations like the "best" app shown in your admin panel.

### Check for Fake Apps:
```powershell
# Audit current consumer apps and detect fake ones
python manage.py validate_consumers

# Check a specific app
python manage.py validate_consumers --consumer best

# Clean up fake apps (dry run first)
python manage.py validate_consumers --check-all --cleanup --dry-run

# Actually remove fake apps
python manage.py validate_consumers --check-all --cleanup --force
```

### For Real App Registration:
1. Apps must register through the system with proper validation
2. Apps must provide a callback URL for health checks
3. Apps must authenticate with API keys and signatures
4. Apps must be explicitly authorized for specific data capabilities

**Example**: The "best" app in your screenshot is flagged as FAKE because it has no validation record.

# Start the tunnel (this will run in the foreground)
Cloud Flare:

Start-Service cloudflared       # start
Stop-Service cloudflared        # stop
Restart-Service cloudflared     # restart
Get-Service cloudflared         # status

To start the tunnel manually (when needed):
1: in another terminal after the back end is running

# Navigate to root directory first
cd A:\Thor

# Start the tunnel (this will run in the foreground)
cloudflared tunnel run thor

> If you see a white screen at https://thor.360edu.org:
> - Make sure Vite dev is running on port 5173 (`npm run dev`) and Django on 8000.
> - Confirm both cloudflared configs point to 5173 for the frontend (`C:\ProgramData\cloudflared\config.yml` and `%USERPROFILE%\.cloudflared\config.yml`).
> - Hard refresh the browser (Ctrl+F5) to clear cached dev assets.

MarketDashboard now fetches:
Latest sessions: http://127.0.0.1:8000/api/futures/market-opens/latest/
Live status: http://127.0.0.1:8000/api/global-markets/markets/live_status/
---

## 7 (Optional) Start Market Open Grader

The Market Open Grader monitors pending MarketSession rows and updates their `wndw` status (WORKED / DIDNT_WORK / NEUTRAL) based on live Redis prices hitting targets.

Run this in a separate terminal:

```powershell
cd A:\Thor\thor-backend

# Start the grader with default 0.5s interval monitors wndw
python manage.py start_market_grader

# Or customize the check interval (in seconds)
python manage.py start_market_grader --interval 1.0
```

Notes:
- Runs continuously until you press Ctrl+C
- Watches all MarketSession rows with `wndw='PENDING'`
- Uses live bid/ask from Redis to determine if target_high or target_low is hit
- For BUY signals: price >= target_high  WORKED, price <= target_low  DIDNT_WORK
- For SELL signals: price <= target_low  WORKED, price >= target_high  DIDNT_WORK
- HOLD signals are marked NEUTRAL automatically
