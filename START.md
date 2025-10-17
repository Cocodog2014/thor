# 🔨 Thor – Developer Quick Start (Windows)

This guide gets the dev stack up quickly on Windows with Anaconda and Docker.
It uses Redis (Docker), Postgres (Docker), Django (conda), and Vite/React.

Prereqs
- Docker Desktop (Windows 11)
- Anaconda/Miniconda (an env that you actually use, e.g., Thor_inv or ThorBot)
- Node.js 18+ (for the frontend) – npm will prompt to install if missing
- Optional: Cloudflare Tunnel (cloudflared) to expose HTTPS in dev

## Step 1: Start Redis (Docker)
Redis powers the live quote bus.

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
```powershell
# Create and run Postgres 15 (data is ephemeral unless you add a volume)
docker run --name thor_postgres `
  -e POSTGRES_DB=thor_db `
  -e POSTGRES_USER=thor_user `
  -e POSTGRES_PASSWORD=thor_password `
  -p 5432:5432 `
  -d postgres:15

# If you choose a different host port, set DB_PORT in A:\Thor\thor-backend\.env accordingly.
```

## Step 3: Start Backend (Django)
```powershell
# From A:\Thor directory:
cd A:\Thor\thor-backend
# Activate your Anaconda env (the one with redis installed)
# Example (update to your actual env name):
conda activate Thor_inv

# Confirm Python is from conda (should NOT be A:\\Thor\\thor-backend\\venv\\...)
where python
# Ensure Redis URL is set (if not already)
$env:REDIS_URL = 'redis://localhost:6379/0'

# Install/refresh backend deps inside THIS conda env
#python -m pip install -r requirements.txt

# Database migrations and (optional) admin user
#python manage.py migrate
# python manage.py createsuperuser   # if you need to create an admin account
# Set environment for Excel Live provider
$env:DATA_PROVIDER = 'excel_live'
$env:EXCEL_DATA_FILE = 'A:\Thor\CleanData.xlsm'
$env:EXCEL_SHEET_NAME = 'Futures'
$env:EXCEL_LIVE_RANGE = 'A1:M20'
# If Excel workbook must already be open, set to '1'; otherwise the provider will open it
$env:EXCEL_LIVE_REQUIRE_OPEN = '0'
python manage.py runserver
```


## Step 4: HTTPS callback for Schwab (Cloudflare Tunnel)

**Why needed:** Schwab OAuth requires HTTPS for callback URLs, but your dev Django server runs on HTTP.

**Solution:** Cloudflare Tunnel terminates TLS and forwards to your local server.

### Quick Setup

1. **Install and authenticate cloudflared** (one-time):
   ```powershell
   # Install (if not already installed)
   choco install cloudflared -y
   
   # Authenticate with Cloudflare
   cloudflared tunnel login
   ```

2. **Create tunnel** (if not exists):
   ```powershell
   # Create tunnel named "thor-local"
   cloudflared tunnel create thor-local
   
   # Route subdomain to tunnel
   cloudflared tunnel route dns thor-local thor.360edu.org
   ```

3. **Create config file** at `%USERPROFILE%\.cloudflared\config.yml`:
   ```yaml
   tunnel: thor-local
   credentials-file: C:\Users\<YourUser>\.cloudflared\<TUNNEL-UUID>.json
   
   ingress:
     - hostname: thor.360edu.org
       service: http://localhost:8000
     - service: http_status:404
   ```

4. **Start tunnel** (run in separate terminal):
   ```powershell
   cd A:\Thor
   cloudflared tunnel run thor-local
   ```

5. **Control via Windows Service** (optional - for auto-start):
   ```powershell
   # Install as Windows service (one-time)
   cloudflared service install
   
   # Control commands
   Start-Service cloudflared       # Start tunnel
   Stop-Service cloudflared        # Stop tunnel
   Get-Service cloudflared         # Check status
   Restart-Service cloudflared     # Restart
   
   # Set startup behavior
   Set-Service cloudflared -StartupType Manual      # Manual start (recommended for dev)
   Set-Service cloudflared -StartupType Automatic   # Auto-start on boot
   ```

### Configure Environment

Update your `.env` file (create from `.env.example` if needed):
```env
# Schwab OAuth credentials (get from developer.schwab.com)
SCHWAB_CLIENT_ID=your_client_id_here
SCHWAB_CLIENT_SECRET=your_client_secret_here

# Cloudflare Tunnel URL (for OAuth callback)
CLOUDFLARE_TUNNEL_URL=https://thor.360edu.org
```

### Update Schwab Developer Portal

Add your callback URL in the Schwab Developer Portal:
- Callback URL: `https://thor.360edu.org/api/schwab/oauth/callback/`

### Test OAuth Flow

1. Start Django: `python manage.py runserver`
2. Start tunnel: `cloudflared tunnel run thor-local` (or `Start-Service cloudflared`)
3. Visit: `http://localhost:8000/api/schwab/oauth/start/`
4. Complete Schwab login → You'll be redirected back with tokens saved

### Verify Connection

Check if OAuth tokens are saved:
```powershell
# From Django shell
python manage.py shell

# Run:
from LiveData.schwab.models import SchwabToken
SchwabToken.objects.all()  # Should show your saved token
```

**Full details:** See `CloudFlare.md` for advanced configuration, auto-recovery, and troubleshooting.

## Step 5: Start Frontend (React)
Open a new terminal:
```powershell
cd A:\Thor\thor-frontend
# First-time only
#npm install
npm run dev
```

## 🎯 URLs to Access
- **Frontend**: http://localhost:5173 (or 5174 if 5173 is busy)
- **Backend API**: http://127.0.0.1:8000/api/
- **Admin Panel**: http://127.0.0.1:8000/admin/ 
  - Email: `admin@360edu.org`
  - Password: `Coco1464#`
- **Custom Login**: http://localhost:5173/auth/login
  - Email: `admin@360edu.org`
  - Password: `Coco1464#`

### LiveData Endpoints (New!)
- **Schwab OAuth Start**: http://localhost:8000/api/schwab/oauth/start/ (redirects to Schwab)
- **Schwab OAuth Callback**: https://thor.360edu.org/api/schwab/oauth/callback/ (Schwab redirects here)
- **TOS Stream Status**: http://localhost:8000/api/feed/tos/status/
- **TOS Subscribe**: http://localhost:8000/api/feed/tos/subscribe/?symbol=AAPL

### Cloudflare Tunnel (Dev Only)
- **Public URL**: https://thor.360edu.org (maps to http://localhost:8000)
- **Control**: Use `Start-Service cloudflared` / `Stop-Service cloudflared` in PowerShell

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