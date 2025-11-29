## Schwab Live Data – What we implemented now (Schwab only)

This page captures exactly what we added for the Charles Schwab integration so you can reference it and know where to resume next week. It focuses only on Schwab.

## What’s in place today

- OAuth2 flow endpoints to start login and handle callback
- Token exchange and file-based persistence
- Provider status/health that reports Schwab readiness and token state
- Dev redirect override so you can use ngrok without changing production settings
- A debug GET endpoint to hit real Schwab API routes with the stored token
- Root-level callback routes to match the Schwab portal

Excel Live remains the default provider (no breaking changes). To view Schwab status, pass `?provider=schwab` or switch via env.

## Endpoints (backend)

- Start OAuth: `GET /api/schwab/auth/login/`
- OAuth callback (app): `GET /api/schwab/auth/callback`
- OAuth callback (root-level convenience):
    - `GET /auth/callback`
    - `GET /schwab/callback`
- Provider status: `GET /api/schwab/provider/status/?provider=schwab`
- Provider health: `GET /api/schwab/provider/health/?provider=schwab`
- Debug raw GET: `GET /api/schwab/debug/get/?path=/v1/accounts`

Files that define these routes:
- `thor-backend/SchwabLiveData/urls.py` (under `/api/schwab/...`)
- `thor-backend/thor_project/urls.py` (root-level `/auth/callback` and `/schwab/callback`)

## Configuration (.env)

Required/environment keys (resolved by python-decouple in `SchwabLiveData/schwab_client.py`):

```
DATA_PROVIDER=excel_live                 # keep this default

# Schwab OAuth / API
SCHWAB_CLIENT_ID=...
SCHWAB_CLIENT_SECRET=...
SCHWAB_BASE_URL=https://api.schwabapi.com
SCHWAB_SCOPES=read

# Redirects
SCHWAB_REDIRECT_URI=https://360edu.org/auth/callback            # production
SCHWAB_REDIRECT_URI_DEV=https://thor.360edu.org/schwab/callback  # dev via Cloudflare

# Optional overrides
SCHWAB_AUTH_URL=   # default: <BASE_URL>/oauth2/authorize
SCHWAB_TOKEN_URL=  # default: <BASE_URL>/oauth2/token
```

Important:
- SCHWAB_REDIRECT_URI_DEV must EXACTLY match the callback configured in the Schwab portal (host + path).
- Keep production redirect (SCHWAB_REDIRECT_URI) unchanged; dev uses the DEV override when present.

## Token storage

On successful exchange, tokens are saved to:
- `thor-backend/data/schwab_tokens.json`

Saved fields include: `access_token`, `refresh_token`, `expires_in`, `expires_at`, `saved_at`.

## How to test end-to-end (today)

1) Run backend on 8000.
2) Start ngrok and copy the HTTPS forwarding URL.
3) Set `SCHWAB_REDIRECT_URI_DEV` in `.env` to `https://<ngrok>.ngrok-free.app/auth/callback` (or `/schwab/callback` if you prefer that route) and ensure the same is configured in the Schwab portal.
4) Visit: `http://localhost:8000/api/schwab/auth/login/`, approve, and complete OAuth.
5) Check status: `http://localhost:8000/api/schwab/provider/status/?provider=schwab`.
     - Expect `tokens.present: true` and `connected: true` (not expired).
6) Optional: Debug API call: `http://localhost:8000/api/schwab/debug/get/?path=/v1/accounts`.

For detailed dev tunnel steps and troubleshooting, see `START.md` (Step 4) and `ngrok.md` in the repo root.

## How it works (under the hood)

- `SchwabLiveData/schwab_client.py`
    - Reads config from env/.env (python-decouple)
    - `build_authorization_url()` constructs the authorize URL
    - `exchange_code_for_token()` posts to token endpoint and saves tokens
    - `health()` reports configured flags and token presence/expiry
    - `get_raw(path)` performs authenticated GETs with the Bearer token

- `SchwabLiveData/providers.py`
    - `SchwabProvider.health_check()` uses client.health() to report
        - `connected = True` when tokens are present and not expired
    - `SchwabProvider.get_latest_quotes()` is not implemented yet (intentionally)

- `SchwabLiveData/views.py`
    - `schwab_auth_start` → redirects to Schwab authorize
    - `schwab_auth_callback` → exchanges `code` for tokens and responds with connection info
    - `SchwabDebugGetView` → proxy to `client.get_raw()` for diagnostics
    - Quotes and totals continue to use Excel Live until Schwab quotes are implemented

- `SchwabLiveData/provider_factory.py`
    - Provider selection honors query string `?provider=` or env; default is Excel Live
    - `get_provider_status()` surfaces provider name, health, and config

## Django settings (dev tunnel support)

- In DEBUG, the project allows `*.ngrok-free.*` domains in `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` so callbacks via ngrok reach Django.

## Where to resume next week

1) Implement real quotes in `SchwabLiveData/providers.py → SchwabProvider.get_latest_quotes()`
     - Use `SchwabApiClient` to call Schwab’s market data endpoints
     - Map fields to the unified quote schema used by `SchwabQuotesView`
     - Handle token expiry (refresh if provided) and basic rate limiting

2) Optionally add specific client helpers in `schwab_client.py` (e.g., `get_quotes(symbols)`)

3) Verify via:
     - `GET /api/schwab/quotes/latest/?provider=schwab`
     - Frontend should work unchanged once the provider returns the normalized rows

## Common pitfalls (quick)

- Callback mismatch → 400 or no callback; ensure portal and `.env` match exactly
- Missing ngrok authtoken → fix ngrok setup before testing OAuth
- CSRF/host blocked → ensure DEBUG and settings include ngrok domains
- Tokens missing/expired → re-run login; check `data/schwab_tokens.json`