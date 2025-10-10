# 🔨 Thor - Norse Mythology Manager

## Quick Start Guide (4 Simple Steps)

Follow these steps IN ORDER to start the Thor application:

## Step 1: Start Redis (Docker)
Redis powers the live quote bus. Use Docker Desktop on Windows 11.

```powershell
# From A:\Thor (repo root)
docker compose up -d redis

# Optional: verify
docker compose ps
docker exec thor_redis redis-cli ping  # expect PONG

# Make Redis URL available to the backend in this session
$env:REDIS_URL = 'redis://localhost:6379/0'
```

## Step 2: Start Database (Docker PostgreSQL)
```bash
docker run --name thor_postgres \
  -e POSTGRES_DB=thor_db \
  -e POSTGRES_USER=thor_user \
  -e POSTGRES_PASSWORD=thor_password \
  -p 5433:5432 \
  -d postgres:13
```

## Step 3: Start Backend (Django)
```powershell
# From A:\Thor directory:
cd A:\Thor\thor-backend
# Activate the Thor_inv conda environment (contains all required packages)
conda activate Thor_inv
# Ensure Redis URL is set (if not already)
$env:REDIS_URL = 'redis://localhost:6379/0'
# Set environment for Excel Live provider
$env:DATA_PROVIDER = 'excel_live'
$env:EXCEL_DATA_FILE = 'A:\Thor\CleanData.xlsm'
$env:EXCEL_SHEET_NAME = 'Futures'
$env:EXCEL_LIVE_RANGE = 'A1:M20'
# If Excel workbook must already be open, set to '1'; otherwise the provider will open it
$env:EXCEL_LIVE_REQUIRE_OPEN = '0'
python manage.py runserver
```



## Step 4: Enable Schwab OAuth for Local Dev (ngrok)
Use ngrok to expose your local Django server over HTTPS so Schwab can call your callback URL.

1) Ensure the backend is running on port 8000
```powershell
cd A:\Thor\thor-backend
conda activate Thor_inv
python manage.py runserver
```

2) Configure ngrok once with your authtoken (from https://dashboard.ngrok.com/get-started/your-authtoken)
```powershell
& "$env:LOCALAPPDATA\Microsoft\WindowsApps\ngrok.exe" config add-authtoken <YOUR_REAL_TOKEN>
```

3) Start the tunnel to your local server and copy the HTTPS Forwarding URL
```powershell
& "$env:LOCALAPPDATA\Microsoft\WindowsApps\ngrok.exe" http 8000
```
It will print something like: https://your-subdomain.ngrok-free.app

4) Update the Schwab callback in BOTH places to match exactly
- Schwab Developer Portal → Callback URL:
  - https://your-subdomain.ngrok-free.app/auth/callback  (or /schwab/callback)

- A:\Thor\thor-backend\.env → add/update:
  - SCHWAB_REDIRECT_URI=https://360edu.org/auth/callback  (production)
  - SCHWAB_REDIRECT_URI_DEV=https://your-subdomain.ngrok-free.app/auth/callback  (dev)

5) Restart Django so .env changes are loaded
```powershell
Ctrl+C   # in the backend terminal
python manage.py runserver
```

6) Start the Schwab OAuth flow and approve
```powershell
# Open in your browser
http://localhost:8000/api/schwab/auth/login/
```

7) Verify tokens and connection
```powershell
# Open in your browser
http://localhost:8000/api/schwab/provider/status/?provider=schwab
```
You should see tokens.present: true and connected: true.

Tip: You’ll need to run ngrok when developing locally. For a stable URL, consider an ngrok reserved domain or Cloudflare Tunnel.

TEST: Ensure OAuth tokens are saved (connected should show true):
http://localhost:8000/api/schwab/provider/status/?provider=schwab

## Step 5: Start Frontend (React)
Open a new terminal:
```powershell
# Activate the Thor_inv conda environment (contains Node.js and npm)
conda activate Thor_inv
cd A:\Thor\thor-frontend
npm run dev
```

## 🎯 URLs to Access
- **Frontend**: http://localhost:5173 (or 5174 if 5173 is busy)
- **Backend API**: http://127.0.0.1:8000/api/
- **Admin Panel**: http://127.0.0.1:8000/admin/ (admin/Coco1464#)

That's it! ⚡

