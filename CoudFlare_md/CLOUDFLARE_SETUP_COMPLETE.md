Hor5173 🌐 Cloudflare Tunnel - Frontend + Backend Setup

**Goal**: Serve both React frontend and Django backend through `thor.360edu.org`

## 🎯 URL Structure

After this setup:
- **`https://thor.360edu.org/`** → React Frontend (Vite, port 5173)
- **`https://thor.360edu.org/admin/`** → Django Admin Panel
- **`https://thor.360edu.org/api/`** → Django API endpoints
- **`https://thor.360edu.org/static/`** → Django static files
- **`https://thor.360edu.org/media/`** → Django media files

---

## ✅ Configuration Complete

The Cloudflare tunnel configuration has been updated at:
`C:\ProgramData\cloudflared\config.yml`

Backup saved as:
`C:\ProgramData\cloudflared\config.yml.backup.YYYYMMDD_HHMMSS`

---

## 🚀 How to Apply Changes

### Step 1: Stop the current cloudflared process

In the **cloudflared** terminal (or open a new PowerShell):

```powershell
# Find and kill the cloudflared process
Get-Process cloudflared | Stop-Process -Force
```

### Step 2: Ensure both services are running

**Terminal 1 (Backend - Django):**
```powershell
cd A:\Thor\thor-backend
python manage.py runserver 0.0.0.0:8000
```

**Terminal 2 (Frontend - React/Vite):**
```powershell
cd A:\Thor\thor-frontend
npm run dev
```

Make sure Vite shows it's listening on **port 5173**.

### Step 3: Start cloudflared with the new config

**Terminal 3 (Cloudflared):**
```powershell
cd A:\Thor
cloudflared tunnel run thor
```

---

## 🧪 Testing

Once all three services are running:

1. **Frontend**: Visit https://thor.360edu.org/
   - Should show your React app login page
   
2. **Admin**: Visit https://thor.360edu.org/admin/
   - Should show Django admin login
   
3. **API**: Visit https://thor.360edu.org/api/
   - Should show API endpoints JSON

4. **Local fallback**: 
   - Frontend: http://localhost:5173
   - Backend: http://localhost:8000

---

## 🔍 Troubleshooting

### Frontend shows 502 Bad Gateway
- Make sure Vite is running on port 5173
- Check: `Get-Process | Where-Object {$_.ProcessName -like "*node*"}`
- Restart: `cd A:\Thor\thor-frontend; npm run dev`

### Backend paths (admin/api) show 502
- Make sure Django is running on port 8000
- Check: `Get-Process python`
- Restart: `cd A:\Thor\thor-backend; python manage.py runserver 0.0.0.0:8000`

### Changes not taking effect
1. Kill cloudflared: `Get-Process cloudflared | Stop-Process -Force`
2. Verify config: `Get-Content C:\ProgramData\cloudflared\config.yml`
3. Restart: `cloudflared tunnel run thor`

### Check what's running
```powershell
# Check all three services
Get-Process cloudflared -ErrorAction SilentlyContinue
Get-Process python -ErrorAction SilentlyContinue  
Get-NetTCPConnection -LocalPort 5173,8000 -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,State
```

---

## 📝 How It Works

Cloudflare Tunnel uses **path-based routing**:

1. Request comes to `thor.360edu.org`
2. Cloudflare checks the path:
   - `/admin/*` or `/api/*` → Forward to `localhost:8000` (Django)
   - Everything else → Forward to `localhost:5173` (React)
3. Local service responds
4. Cloudflare returns response over HTTPS

**Benefits:**
- ✅ Single domain for everything
- ✅ HTTPS everywhere (Cloudflare handles certificates)
- ✅ No CORS issues between frontend/backend
- ✅ Works for Schwab OAuth callbacks
- ✅ Professional setup

---

## 🔄 Quick Reference Commands

```powershell
# Start everything (3 terminals)

# Terminal 1: Backend
cd A:\Thor\thor-backend
python manage.py runserver 0.0.0.0:8000

# Terminal 2: Frontend  
cd A:\Thor\thor-frontend
npm run dev

# Terminal 3: Cloudflare Tunnel
cd A:\Thor
cloudflared tunnel run thor

# Check status
Get-Process cloudflared,python
netstat -ano | findstr "5173 8000"

# Stop tunnel
Get-Process cloudflared | Stop-Process -Force

# View tunnel logs
cloudflared tunnel run thor --loglevel debug
```

---

## 🎨 Next Steps

1. **Update Django ALLOWED_HOSTS** if needed (should already include thor.360edu.org)
2. **Update Frontend API URLs** to use relative paths (they already proxy correctly)
3. **Test Schwab OAuth** through https://thor.360edu.org/api/schwab/auth/login/
4. **Set up Cloudflare Access** if you want authentication before reaching the app

---

**Status**: ✅ Configuration complete. Restart cloudflared to apply!
