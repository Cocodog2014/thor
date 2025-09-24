SchwabLiveData app: lean provider setup

What changed
- Removed unused JSON variation files (futures_data_variation_*.json). The app now uses a single dev file: futures_data.json when DATA_PROVIDER=json.
- Consolidated Excel Live provider into excel_live.py and referenced it from providers.py to avoid duplication.
- Added schwab_client.py: a minimal SchwabApiClient scaffold that reports configuration readiness. No real API calls until credentials are provided.

How to run providers
- Excel file (recommended): set EXCEL_DATA_FILE to the workbook path and DATA_PROVIDER=excel.
- Excel Live (open workbook via COM): set DATA_PROVIDER=excel_live and optionally EXCEL_LIVE_REQUIRE_OPEN=1, EXCEL_LIVE_RANGE=A1:M20.
- JSON (dev only): set DATA_PROVIDER=json and (optionally) JSON_DATA_FILE.

Preparing for Schwab
- Set SCHWAB_CLIENT_ID, SCHWAB_CLIENT_SECRET, SCHWAB_REDIRECT_URI, SCHWAB_SCOPES and then set DATA_PROVIDER=schwab. The status endpoints will reflect configuration, but quote fetching will remain disabled until API access is granted.
