# Environment Variables

Backend:
- `DATA_PROVIDER`: `excel_live` | `schwab_live`
- `EXCEL_DATA_FILE`: path to `RTD_TOS.xlsm`
- `EXCEL_SHEET_NAME`: e.g., `LiveData`
- `EXCEL_LIVE_RANGE`: e.g., `A1:N13`
- `REDIS_URL`: `redis://localhost:6379/0`
- `DISABLE_GLOBAL_MARKETS_MONITOR`: `1` to disable during migrations
- `FUTURETRADING_ENABLE_52W_MONITOR`: `0/1`
- Supervisor intervals (examples):
  - `FUTURETRADING_52W_MONITOR_INTERVAL`
  - `FUTURETRADING_52W_SUPERVISOR_INTERVAL`

Frontend:
- Vite envs as needed (document if used)

Add more vars here as they become canonical.
