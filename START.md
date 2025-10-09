# 🔨 Thor - Norse Mythology Manager

## Quick Start Guide (3 Simple Steps)

Follow these steps IN ORDER to start the Thor application:

## Step 1: Start Database (Docker PostgreSQL)
```bash
docker run --name thor_postgres \
  -e POSTGRES_DB=thor_db \
  -e POSTGRES_USER=thor_user \
  -e POSTGRES_PASSWORD=thor_password \
  -p 5433:5432 \
  -d postgres:13
```

## Step 2: Start Backend (Django)
```powershell
# From A:\Thor directory:
cd A:\Thor\thor-backend
# Activate the Thor_inv conda environment (contains all required packages)
conda activate Thor_inv
# Set environment for Excel Live provider
$env:DATA_PROVIDER = 'excel_live'
$env:EXCEL_DATA_FILE = 'A:\Thor\CleanData.xlsm'
$env:EXCEL_SHEET_NAME = 'Futures'
$env:EXCEL_LIVE_RANGE = 'A1:M20'
# If Excel workbook must already be open, set to '1'; otherwise the provider will open it
$env:EXCEL_LIVE_REQUIRE_OPEN = '0'
python manage.py runserver
```

## Step 3: Start Frontend (React)
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
- **Admin Panel**: http://127.0.0.1:8000/admin/ (admin/Coco1464#

That's it! ⚡

