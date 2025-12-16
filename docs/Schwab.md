# Thor Schwab Integration Guide

Single source of truth for everything related to our Charles Schwab Trading API integration: OAuth, token refresh, backend endpoints, Redis publishing, and how the frontend should consume balances/positions.

---

## 1. Capabilities Overview

| Feature | Status | Notes |
|---------|--------|-------|
| OAuth 2.0 login & callback | ✅ | `/api/schwab/oauth/start/` and `/api/schwab/oauth/callback/` persist tokens in `BrokerConnection` |
| Token auto-refresh | ✅ | `ensure_valid_access_token()` refreshes early, uses Redis-style lock, and 401 retry fallback |
| Account list + summaries | ✅ | `/api/schwab/accounts/`, `/api/schwab/account/summary/`, `/account_statement/real/schwab/summary/` |
| Balances + Redis publish | ✅ | `/api/schwab/accounts/<account>/balances/` pumps normalized payloads into `live_data:balances:{account}` |
| Positions + Redis publish | ✅ | `/api/schwab/accounts/<account>/positions/` streams to `live_data:positions:{account}` |
| RealAccount persistence | ✅ | Account Statement endpoint formats Schwab data and stores it in `account_statement_realaccount` |
| Order placement | ⬜ | Not implemented; future work once trading is enabled |

---

## 2. Architecture & Flow

```
User                Django + Thor Backend                                Schwab API
----                ----------------------                                ----------
Click "Connect" →  /api/schwab/oauth/start/  → redirect to Schwab --------→
                    ← /api/schwab/oauth/callback/?code=... ← tokens ←------
                    BrokerConnection saved (access, refresh, expiry)
                    ↓
Frontend calls data endpoints (accounts / balances / positions / summary)
                    ↓
SchwabTraderAPI ensures valid token → calls Schwab APIs → normalizes payloads
                    ↓
Redis publish (live_data:balances:*, live_data:positions:*) + DB persistence
```

---

## 3. Configuration (.env + settings)

Set once and share between containers:

```bash
# OAuth credentials (from developer.schwab.com)
SCHWAB_CLIENT_ID=...
SCHWAB_CLIENT_SECRET=...
SCHWAB_ENV=production
SCHWAB_SCOPES=api

# Callback – **must** match Schwab portal entry exactly (including trailing slash)
SCHWAB_REDIRECT_URI=https://dev-thor.360edu.org/api/schwab/oauth/callback/
SCHWAB_REDIRECT_URI_DEV=https://dev-thor.360edu.org/api/schwab/oauth/callback/

# Optional overrides (defaults are fine for prod)
SCHWAB_BASE_URL=https://api.schwabapi.com
SCHWAB_AUTHORIZE_URL=https://api.schwabapi.com/v1/oauth/authorize
SCHWAB_TOKEN_URL=https://api.schwabapi.com/v1/oauth/token
SCHWAB_TOKEN_EXPIRY_BUFFER=60  # seconds to refresh early
```

In `thor_project/settings.py` ensure:

```python
SCHWAB_TOKEN_EXPIRY_BUFFER = int(os.getenv("SCHWAB_TOKEN_EXPIRY_BUFFER", "60"))
```

For tunnel testing (ngrok/cloudflared) keep `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` aligned with the public URL, and update both the Schwab portal callback and `.env` before triggering OAuth.

---

## 4. OAuth & Token Lifecycle

* `LiveData/schwab/tokens.py`
  * `exchange_code_for_tokens()` swaps the auth code for access + refresh tokens and saves them to `BrokerConnection`.
  * `ensure_valid_access_token()` guards every outgoing request:
    * Applies the configured buffer (default 60 s) so we refresh *before* expiry.
    * Wraps refresh logic in a short-lived cache lock (`schwab:refresh:<user_id>`) so parallel requests don’t double-refresh.
    * Rechecks the DB record once the lock is acquired.
    * Logs and proceeds if the lock can’t be acquired.
  * `SchwabTraderAPI` calls `ensure_valid_access_token()` inside `__init__`, so any view using the API client automatically refreshes tokens.
  * `_request()` wraps outbound HTTP calls. A `401 Unauthorized` triggers a forced refresh and a single retry before it raises.

Access tokens last ~30 minutes (`expires_in=1800`). Refresh tokens last ~7 days. We refresh automatically; the user only needs to re-run OAuth when Schwab invalidates the refresh token (e.g., password change, 7‑day timeout).

---

## 5. Backend Endpoints

### 5.1 `/api/schwab/*` (LiveData app)

| Endpoint | Purpose | Notes |
|----------|---------|-------|
| `GET /api/schwab/oauth/start/` | Build Schwab authorize URL | Redirect-only JSON response |
| `GET /api/schwab/oauth/callback/` | Exchange `code` for tokens | Redirects back to `FRONTEND_BASE_URL/?status=connected` |
| `GET /api/schwab/accounts/` | List Schwab accounts | Persists/creates `ActAndPos.Account` rows |
| `GET /api/schwab/accounts/<acct>/balances/` | Normalize + publish balances | Publishes to `live_data:balances:{acct}`, returns payload + channel |
| `GET /api/schwab/accounts/<acct>/positions/` | Normalize + publish positions | Publishes to `live_data:positions:{acct}` |
| `GET /api/schwab/account/summary/` | Fetch balances for UI | Calls balances endpoint internally, returns formatted strings |

All endpoints require Django auth (`IsAuthenticated`). They depend on `request.user.schwab_token` having an active `BrokerConnection` row.

### 5.2 `/account_statement/real/schwab/summary/`

Located in `account_statement/views/real.py`. This endpoint:

1. Uses `SchwabTraderAPI` to fetch the summary payload.
2. Creates or updates `account_statement.RealAccount` with the latest balances (net liq, buying powers, long stock value, maintenance requirement, etc.).
3. Returns a frontend-ready JSON response containing the formatted numbers and metadata (account hash, last sync timestamp).

Use this endpoint whenever the UI needs a persisted snapshot (e.g., Account Statement dashboards). For raw/ephemeral data, use `/api/schwab/account/summary/`.

---

## 6. Data Publishing & Persistence

* **Redis** (`LiveData/shared/redis_client.py`)
  * `publish_balance(account_id, payload)` → `live_data:balances:{account_id}`
  * `publish_position(account_id, payload)` → `live_data:positions:{account_id}`
* **Database models**
  * `ActAndPos.Account` – used for mapping Schwab accounts to Thor accounts when listing accounts.
  * `account_statement.RealAccount` – stores the persisted summaries for reporting.

`SchwabTraderAPI.fetch_balances()` pulls from `/trader/v1/accounts`, normalizes buying power fields, persists them, and returns a dict consumable by the UI.

`SchwabTraderAPI.fetch_positions()` uses `/accounts/{id}?fields=positions` to normalize holdings and publish each symbol to Redis.

---

## 7. Testing & Verification

### 7.1 Complete OAuth (one time per user)
1. Visit `http://localhost:8000/api/schwab/oauth/start/`.
2. Login + approve in the Schwab portal.
3. Confirm redirect back to `FRONTEND_BASE_URL/?broker=schwab&status=connected`.

### 7.2 Validate tokens quickly
```bash
python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
user = get_user_model().objects.first()
conn = getattr(user, 'schwab_token', None)
print('Connected:', bool(conn))
print('Expired:', conn.is_expired if conn else '—')
PY
```

### 7.3 Hit data endpoints
```bash
# Accounts
curl -s -b cookies.txt http://localhost:8000/api/schwab/accounts/ | python -m json.tool

# Balances + Redis channel info
curl -s -b cookies.txt http://localhost:8000/api/schwab/accounts/<acct>/balances/

# Account Statement summary (persists RealAccount)
curl -s -b cookies.txt http://localhost:8000/account_statement/real/schwab/summary/ | python -m json.tool
```

### 7.4 Force-refresh test
```bash
python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
user = get_user_model().objects.first()
conn = user.schwab_token
conn.access_expires_at = 0
conn.save(update_fields=['access_expires_at'])
PY
```
Then call any `/api/schwab/*` endpoint; logs should show `Schwab OAuth: refresh successful` once, and the request should succeed.

---

## 8. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| 404 “No Schwab account connected” | User hasn’t completed OAuth | Run `/api/schwab/oauth/start/` and finish login |
| 401 from Schwab even after retry | Refresh token expired or revoked | Clear `BrokerConnection` row for user and redo OAuth |
| 400 redirect mismatch | Callback URL in Schwab portal doesn’t match `.env` | Update both locations and redeploy |
| Redis subscribers don’t receive balances | Endpoint not called or Redis down | Hit `/api/schwab/accounts/<acct>/balances/` and check Redis logs |
| Duplicate VWAP rows / workers start twice | (Handled) – ensure Django `RUN_MAIN` guard is in place (`ThorTrading/apps.py`) |

---

## 9. File Map

```
thor-backend/
├── LiveData/schwab/
│   ├── tokens.py              # OAuth exchange + refresh helper
│   ├── services.py            # SchwabTraderAPI client + Redis publishing
│   ├── views.py               # REST endpoints (accounts, balances, positions, summary)
│   └── urls.py                # /api/schwab/* routes
├── account_statement/
│   ├── views/real.py          # Schwab summary persistence endpoint
│   └── urls/real.py           # /account_statement/real/* routes
├── LiveData/shared/redis_client.py
└── docs/Schwab.md             # ← this document
```

---

## 10. Backlog / Next Steps

1. **Order routing** – add endpoints for placing/canceling Schwab orders (requires trading enablement toggle).
2. **Streaming quotes** – implement Schwab market data provider to replace the Excel feed where possible.
3. **Frontend polish** – wire `/account_statement/real/schwab/summary/` into the Stock Trading dashboard and add live balance indicators sourced from Redis.
4. **Monitoring** – add metrics/alerts for token refresh failures and Redis publish errors.

With this doc, the previous scattered files (`LiveData/schwab/Schwab.md`, `docs/Schwab_md/*`) are no longer needed. Keep this file updated whenever we touch the Schwab integration.
