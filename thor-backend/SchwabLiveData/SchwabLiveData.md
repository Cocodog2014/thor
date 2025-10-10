# SchwabLiveData App Documentation

## Overview

The SchwabLiveData app is responsible for ALL live market data collection and formatting. It manages multiple data providers and exposes a consistent API to the rest of the system.

## Architecture principle

- Owns: Raw data collection, provider selection, and display formatting
- Does not own: Trading formulas, signal classification, or business logic

## Files and modules

### Core provider system

#### `providers.py`
Purpose: Core data provider implementations
- BaseProvider – abstract interface for all providers
- ExcelLiveProvider – live Excel via xlwings (polling thread)
- SchwabProvider – scaffold for Schwab API; reports health using stored OAuth tokens

Key features:
- Symbol-specific display precision (e.g., YM=0, ES=2, SI=3, HG=4)
- Consistent, normalized data structure across providers
- Health metadata including token presence and expiry (for Schwab)

#### `excel_live.py`
Purpose: Real-time Excel integration using xlwings
- Connects to running workbooks and polls a configured range
- Background thread with configurable polling interval
- Canonicalizes symbols (/YM vs YM)

#### `provider_factory.py`
Purpose: Provider selection and configuration management
- ProviderConfig – resolves env + request overrides (e.g., ?provider=schwab)
- get_market_data_provider – creates/caches provider instance
- get_provider_status – returns active provider name, health, and key config

### API layer

#### `views.py`
Purpose: REST API endpoints
- SchwabQuotesView – unified quotes endpoint: `/api/schwab/quotes/latest/`
- ProviderStatusView – provider selection + status: `/api/schwab/provider/status/`
- ProviderHealthView – health only: `/api/schwab/provider/health/`
- OAuth endpoints:
  - Start login: `/api/schwab/auth/login/`
  - Callback: `/api/schwab/auth/callback` (also `/auth/callback` and `/schwab/callback` at project root)
- Debug endpoint:
  - Raw GET passthrough: `/api/schwab/debug/get/?path=/v1/accounts`

Notes:
- Provider selection respects `?provider=schwab` or `DATA_PROVIDER` env; Excel stays default.
- Quotes are enriched with DB values (signals/weights) and produce a composite total.

#### `urls.py`
Purpose: App URL routing for the endpoints above.

### Integration components

#### `schwab_client.py`
Purpose: Schwab API client (OAuth2 + simple GETs for diagnostics)
- Reads config from env/.env via python-decouple
- Constructs auth URL; exchanges code for tokens via `oauth2/token`
- Saves tokens to `thor-backend/data/schwab_tokens.json`
- Exposes `health()` with token presence/expiry and effective config
- Provides `get_raw(path)` to exercise real API calls with Bearer token

#### `models.py` and `admin.py`
Currently minimal; no additional models are required for provider operation.

## Data flow

1) provider_factory.py → Choose provider (Excel Live or Schwab)
2) providers.py → Fetch/normalize raw data
3) views.py → Enrich with DB values and return REST responses
4) excel_live.py → If selected, supplies live Excel updates

## Provider configuration

### Environment variables
```bash
# Primary selection (Excel Live remains the default to avoid breaking workflows)
DATA_PROVIDER=excel_live   # or schwab

# Excel Live
EXCEL_DATA_FILE=A:\\Thor\\CleanData.xlsm
EXCEL_SHEET_NAME=Futures
EXCEL_LIVE_RANGE=A1:M20
EXCEL_LIVE_REQUIRE_OPEN=0   # 0=auto-open, 1=require already open
EXCEL_LIVE_POLL_MS=200

# Schwab OAuth / API
SCHWAB_CLIENT_ID=your_client_id
SCHWAB_CLIENT_SECRET=your_secret
SCHWAB_BASE_URL=https://api.schwabapi.com
SCHWAB_AUTH_URL=            # optional override; defaults to <BASE_URL>/oauth2/authorize
SCHWAB_TOKEN_URL=           # optional override; defaults to <BASE_URL>/oauth2/token
SCHWAB_SCOPES=read
SCHWAB_REDIRECT_URI=        # production redirect (e.g., https://360edu.org/auth/callback)
SCHWAB_REDIRECT_URI_DEV=    # dev redirect (e.g., https://<ngrok>.ngrok-free.app/auth/callback)
```

Tip: Ensure SCHWAB_REDIRECT_URI and SCHWAB_REDIRECT_URI_DEV are on separate lines in `.env`.

## OAuth quickstart (safe, non-breaking)

Excel Live stays the default provider. You can fully complete OAuth and persist tokens without switching providers.

1) Configure env in `thor-backend/.env`:
	- SCHWAB_CLIENT_ID and SCHWAB_CLIENT_SECRET from the Schwab portal
	- SCHWAB_REDIRECT_URI for production (keep as-is)
	- SCHWAB_REDIRECT_URI_DEV set to your ngrok HTTPS URL + `/auth/callback` (or `/schwab/callback`)

2) Start Django locally on port 8000, then start ngrok and copy the HTTPS forwarding URL.
	- See repo root `START.md` Step 4 and `ngrok.md` for commands and troubleshooting.

3) Update the Schwab Developer Portal to use the same callback URL you set in `.env`.

4) Begin OAuth and approve access:
	- Open: `http://localhost:8000/api/schwab/auth/login/`

5) Tokens are exchanged and saved automatically to `thor-backend/data/schwab_tokens.json`.
	- Verify: `http://localhost:8000/api/schwab/provider/status/?provider=schwab`
	- You should see `tokens.present: true` and `connected: true` when not expired.

6) Optional: Test a real Schwab API GET using stored tokens:
	- `http://localhost:8000/api/schwab/debug/get/?path=/v1/accounts`

## Troubleshooting

- Callback mismatch: The URL in the Schwab portal must exactly match the one used by your dev tunnel (`SCHWAB_REDIRECT_URI_DEV`).
- Ngrok/CSRF in Django: In DEBUG, the project includes the `*.ngrok-free.*` domains in `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
- Authtoken error (ERR_NGROK_105): Ensure you added a real ngrok authtoken.
- No tokens shown: Re-run the login URL and complete consent. Check `data/schwab_tokens.json` for saved tokens.

## Provider options

- Excel Live – real-time Excel via xlwings (recommended for continuity)
- Schwab – OAuth and health implemented; quotes endpoint wiring ready for future API mapping

Once Schwab’s quotes/market-data endpoints and entitlements are confirmed, the `SchwabProvider.get_latest_quotes` method can map responses into the existing schema used by `SchwabQuotesView`.
