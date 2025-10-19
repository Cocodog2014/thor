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
conda activate Thor_inv

# Set environment variables for Excel Live data
$env:DATA_PROVIDER = 'excel_live'
$env:EXCEL_DATA_FILE = 'A:\Thor\CleanData.xlsm'
$env:EXCEL_SHEET_NAME = 'Futures'
$env:EXCEL_LIVE_RANGE = 'A1:M20'
$env:REDIS_URL = 'redis://localhost:6379/0'

# Start Django
python manage.py runserver
```

---

## 4️⃣ Start Frontend (Optional)

```powershell
cd A:\Thor\thor-frontend
npm run dev
```

---

## 📌 Important URLs

### Local Access
- **Backend API**: http://localhost:8000/api/
- **Admin Panel**: http://localhost:8000/admin/
  - Email: `admin@360edu.org`
  - Password: `Coco1464#`
- **Frontend**: http://localhost:5173

### Schwab OAuth
- **Start OAuth**: http://localhost:8000/api/schwab/oauth/start/
- **Callback URL**: https://thor.360edu.org/api/schwab/oauth/callback/

### Cloudflare Tunnel
- **Public URL**: https://thor.360edu.org

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
