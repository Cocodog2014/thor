cd A:\Thor
.\thor_dev.ps1

http://localhost:5173/


1. Start databases & cache

```powershell
cd A:\Thor
docker compose up -d postgres
docker compose up -d redis
```

2. Run backend (new shell)

```powershell
cd A:\Thor\thor-backend
# conda activate ThorBot       # if applicable
$env:DATA_PROVIDER    = 'excel_live'
$env:EXCEL_DATA_FILE  = 'A:\\Thor\\RTD_TOS.xlsm'
$env:EXCEL_SHEET_NAME = 'LiveData'
$env:EXCEL_LIVE_RANGE = 'A1:N13'
$env:REDIS_URL        = 'redis://localhost:6379/0'
# optional: disable background 52-week monitor
# $env:FUTURETRADING_ENABLE_52W_MONITOR = '0'
python manage.py runserver
```

3. Run frontend

```powershell
cd A:\Thor\thor-frontend
npm run dev
```

4. Start Excel → Redis poller (new shell)

```powershell
cd A:\Thor\thor-backend
python manage.py poll_tos_excel
```

5. (Optional) Run Cloudflare Tunnel (dev)

```powershell
cd A:\Thor
cloudflared tunnel run thor
```


6. (Optional) Start Market Open Grader (new shell)

The grader monitors pending MarketSession rows and updates their `wndw` field based on live prices hitting targets.

```powershell
cd A:\Thor\thor-backend

# Start with default 0.5s check interval
python manage.py start_market_grader

# Or customize interval
python manage.py start_market_grader --interval 1.0

### Local Access
- **Backend API**: http://localhost:8000/api/
- **Admin Panel**: http://localhost:8000/admin/
  - Email: `admin@360edu.org`
  - Password: `Coco1464#`
- **Frontend**: http://localhost:5173

to run Gunicorn in docker desk top 

cd A:\Thor
docker compose up -d

http://localhost:8001/admin/
