# thor_dev.ps1
# One-command launcher for the entire Thor development stack

Write-Host ""
Write-Host "==========================="
Write-Host "  Starting Thor Dev Stack  "
Write-Host "==========================="
Write-Host ""

# 1. Start Docker containers
Write-Host "Starting Redis & Postgres..."
cd "A:\Thor"
docker compose up -d postgres
docker compose up -d redis

Start-Sleep -Seconds 2

# 2. Start Django backend in a new terminal window
Write-Host "Starting Django Backend..."
$backendCommand = @"
cd 'A:\Thor\thor-backend';
`$env:DATA_PROVIDER    = 'excel_live';
`$env:EXCEL_DATA_FILE  = 'A:\Thor\RTD_TOS.xlsm';
`$env:EXCEL_SHEET_NAME = 'LiveData';
`$env:EXCEL_LIVE_RANGE = 'A1:N13';
`$env:REDIS_URL        = 'redis://localhost:6379/0';
python manage.py runserver;
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand

Start-Sleep -Seconds 1

# 3. Start React frontend in another terminal window
Write-Host "Starting React Frontend..."
$frontendCommand = @"
cd 'A:\Thor\thor-frontend';
npm run dev;
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCommand

Write-Host ""
Write-Host "Thor Dev Stack launch command finished."
Write-Host "Two new terminals should now be open:"
Write-Host " - Backend (Django + supervisors)"
Write-Host " - Frontend (React dev server)"
Write-Host ""
Write-Host "If nothing opens, tell me the message shown here."

