import time, os, json
from SchwabLiveData.excel_live import ExcelLiveProvider

# Config from env or defaults
file_path = os.getenv('EXCEL_DATA_FILE', r'A:\Thor\CleanData.xlsm')
sheet = os.getenv('EXCEL_SHEET_NAME', 'Futures')
range_addr = os.getenv('EXCEL_LIVE_RANGE', 'A1:M20')
require_open = os.getenv('EXCEL_LIVE_REQUIRE_OPEN', '0').lower() in ('1','true','yes','on')

print('Excel Live Debug')
print(' File:', file_path)
print(' Sheet:', sheet)
print(' Range:', range_addr)
print(' Require Open:', require_open)

prov = ExcelLiveProvider(file_path=file_path, sheet_name=sheet, range_address=range_addr, require_open=require_open)

for i in range(5):
    snap = prov.get_latest_quotes()
    rows = snap.get('rows')
    meta = snap.get('meta')
    print(f'Iteration {i}: rows={len(rows)} last_update={meta.get("ts") if meta else None}')
    if rows:
        print(' First row instrument:', rows[0]['instrument']['symbol'])
        print(' Sample row keys:', list(rows[0].keys()))
        break
    time.sleep(0.5)

print('Health check:', prov.health_check())
