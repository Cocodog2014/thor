# Thor Trading ↔ Schwab OAuth Flow (Frontend + Django API)

This document describes the **current end-to-end Schwab connection flow** across:
- **Frontend (React / Vite)**
- **Backend (Django + DRF)**
- **Cloudflare/Tunnel domain**: `https://dev-thor.360edu.org`

---

## 0) Key URLs and Rules

### Frontend base
- App runs at: `https://dev-thor.360edu.org`

### Backend API base
- All API calls go through: `https://dev-thor.360edu.org/api/...`

### Axios rule (IMPORTANT)
Your `api` axios instance uses a `baseURL` that ends with `/api`.
So:
- ✅ `api.get('schwab/oauth/start/')` → hits `/api/schwab/oauth/start/`
- ❌ `api.get('/schwab/oauth/start/')` → hits `/schwab/oauth/start/` (WRONG; ignores baseURL)

---

## 1) User clicks "Setup Brokerage Account" (Frontend → Backend)

### UI triggers
- Banner button: **Setup Brokerage Account**
- Or Broker Connections page button: **Connect Schwab**

### Frontend action
- React calls backend to get the Schwab authorize URL:

**Request**
- `GET /api/schwab/oauth/start/`

**Frontend example**
```typescript
api.get('schwab/oauth/start/')
```

### Backend action (`oauth_start`)
- Backend builds Schwab authorize URL using:
  - `client_id` (Schwab app key, raw without suffix)
  - `redirect_uri` (must match Schwab Developer Portal callback exactly)
  - `response_type=code`
  - `scope=api` (standard Schwab scope)

**Response**
```json
{ "auth_url": "https://api.schwabapi.com/v1/oauth/authorize?client_id=...&redirect_uri=...&response_type=code&scope=api" }
```

### Frontend redirect
Browser navigates to `auth_url` (Schwab login site).

---

## 2) Schwab Login + Account Linking (Schwab-hosted)

User logs into Schwab and confirms account linking/authorization.

Schwab then redirects back to the registered callback:

```
https://dev-thor.360edu.org/schwab/callback?code=<auth_code>
```

Query params:
- `code=...` (success)
- `error=...` (failure)

---

## 3) Frontend Callback Page (Schwab → React)

### Route
- React route/page: `/schwab/callback`

### Responsibility
This page (`SchwabCallbackPage.tsx`):
1. Read query params from the URL (`code`, `error`, etc.)
2. If `error`, show message and stop
3. If `code`, send it to backend to exchange for tokens

---

## 4) Exchange Authorization Code for Tokens (Schwab → Frontend → Backend)

### Schwab callback redirect
After user authorizes, Schwab redirects to:
```
https://dev-thor.360edu.org/schwab/callback?code=<authorization_code>
```

### Frontend action (SchwabCallbackPage)
Callback page extracts the `code` query param and exchanges it for tokens:

**Request**
- `GET /api/schwab/oauth/callback/?code=...`

**Frontend example**
```typescript
const code = new URLSearchParams(window.location.search).get('code');
if (code) {
  const response = await api.get('schwab/oauth/callback/', { params: { code } });
  // Handle response
}
```

### Backend action (oauth_callback view)
Backend (`@api_view(['GET'])` with `@permission_classes([IsAuthenticated])`):

1. **Validates** user is authenticated via JWT token (from `Authorization: Bearer <token>` header)
2. **Extracts** authorization code from query params: `request.GET.get('code')`
3. **Exchanges code** for tokens:
   - Calls `exchange_code_for_tokens(code)` function
   - Sends to Schwab token endpoint (`https://api.schwabapi.com/v1/oauth/token`):
     - `grant_type=authorization_code`
     - `code`
     - `redirect_uri` (must match exactly)
     - `client_id@AMER.OAUTHAP` (**suffix required for token endpoint only**)
     - `client_secret`
   - Receives:
     - `access_token`
     - `refresh_token`
     - `expires_in` (seconds until expiry)
4. **Stores tokens** using `BrokerConnection.objects.update_or_create()`:
   - Tied to `request.user` (the authenticated Thor user)
   - Stores `access_token`, `refresh_token`, `access_expires_at`
5. **Sends user back to the frontend** once tokens are saved. Instead of returning JSON, the backend issues a redirect:

```
https://dev-thor.360edu.org/?broker=schwab&status=connected
```

React listens for those query params (or simply reloads the dashboard) and then calls the post-connect endpoints.

**Error responses**
- `400`: `{ "error": "No authorization code provided" }`
- `500`: `{ "error": "<exception message>" }`

---

## 5) Post-Connect: Sync Accounts / Balances / Positions (Frontend → Backend)

Once tokens exist, frontend can call:

- **Accounts list**: `GET /api/schwab/accounts/`
  - Returns the raw Schwab `/trader/v1/accounts` payload plus helper fields: `thor_account_id` (local DB row) and `broker_account_id` (the Schwab `hashValue`).
  - Account numbers → hashes are cached in Redis for 60s to reduce `/accounts/accountNumbers` calls.
- **Account summary** (preferred): `GET /api/schwab/account/summary/?account_number=60910485`
  - No `hashValue` required. Resolves hash via cached map, formats balances (net liq, buying powers, available funds, equity %), and defaults to the first account if no query param is provided.
- **Positions** (preferred): `GET /api/schwab/account/positions/?account_number=60910485`
  - Accepts `account_number` or `account_hash`. Publishes to Redis and caches a snapshot (TTL ~5 min) for fallback.
- **Balances** (legacy path): `GET /api/schwab/accounts/<account_id>/balances/`
  - Accepts `account_id` as number or hash. Publishes to Redis and caches a snapshot (TTL ~5 min) for fallback.
- **Positions** (legacy path): `GET /api/schwab/accounts/<account_id>/positions/`
  - Kept for compatibility; prefers the query-param endpoint above.

Resilience:
- If Schwab fails during a fetch, balances/positions endpoints return the last cached snapshot when available (Redis-backed, ~5 minute TTL) instead of empty data.

Frontend uses these results to:
- Populate account dropdowns with Schwab account numbers
- Flip the banner to **Live: Schwab <DisplayName>**
- Display balances/positions pulled from Schwab API or cached last-good snapshots

---

## 6) Account Modes (Paper vs Live)

### Paper Account (default on signup)
- User gets a paper account with $100,000.00
- No Schwab OAuth required
- No real account data is used

### Live Account Mode
- Requires Schwab OAuth connection for that user
- After connection, UI can switch from:
  - "Mode: Paper"
  - to "Live: Schwab <AccountName>"

---

## 7) Common Failure Points + Diagnosis

### A) "Unable to start Schwab OAuth (missing URL)"
**Cause**: Frontend hit the wrong endpoint or got HTML/redirect instead of JSON.

**Fix**:
- Use relative path (no leading slash):
  - ✅ `api.get('schwab/oauth/start/')`
  - ❌ `api.get('/schwab/oauth/start/')`
- Confirm in Network tab:
  - Request must be `GET https://dev-thor.360edu.org/api/schwab/oauth/start/`
  - Response must include `auth_url`

### B) 302 Redirect in Network logs
**Cause**: Backend thinks you are not authenticated and redirects to login.

**Fix**:
- Ensure Schwab endpoints use DRF auth (JWT) consistently (not Django session-only decorators)
- Ensure Authorization header is present:
  - `Authorization: Bearer <access-token>`

### C) Schwab "invalid_client / Unauthorized"
**Cause**: Schwab rejects the authorize request. Usually one of:
- **redirect_uri mismatch**: must match Developer Portal callback exactly
- **client_id suffix**: authorize endpoint uses raw `client_id` (no `@AMER.OAUTHAP`), token endpoint uses `client_id@AMER.OAUTHAP`
- **environment mismatch**: Schwab app registered as Production but backend sending dev URLs
- **scope mismatch**: scope in request must match app settings

**Fix**:
1. Verify in Schwab Developer Portal:
   - App is set to Production (or Sandbox if testing)
   - Callback URL matches exactly what's in `SCHWAB_REDIRECT_URI`
   - Required scopes are enabled
2. Verify in `.env`:
   - `SCHWAB_ENV=production` (must match portal environment)
   - `SCHWAB_REDIRECT_URI=https://dev-thor.360edu.org/schwab/callback`
   - `SCHWAB_CLIENT_ID` is correct (raw ID without suffix)
3. Restart Django backend after `.env` changes
4. Check browser Network tab:
   - Authorize request URL in address bar (verify client_id and redirect_uri)
   - Schwab response error message (may indicate exact issue)

### D) `/api/schwab/account/summary/` returns "Unable to get account identifier"
**Current behavior**: The endpoint no longer requires `hashValue`; it streams balances directly from `/accounts`. If you still see this error, it usually means `fetch_accounts()` returned no data (token expired or Schwab outage).

**Fix**:
- Hit `/api/schwab/accounts/` first. If that returns accounts, summary will work. If it fails, troubleshoot the token/Schwab status.

---

## 8) Minimal "Happy Path" Checklist

- [ ] User logged into Thor (JWT present in localStorage)
- [ ] Click **Setup Brokerage Account** button
- [ ] `GET /api/schwab/oauth/start/` returns `{ "auth_url": "..." }`
- [ ] Browser redirects to Schwab login page
- [ ] User logs in and authorizes Thor
- [ ] Schwab redirects to `/schwab/callback?code=...`
- [ ] Frontend callback page exchanges code via `GET /api/schwab/oauth/callback/?code=...`
- [ ] Backend stores tokens and returns `{ "success": true }`
- [ ] Frontend calls `/api/schwab/accounts/` and updates UI to **Live: Schwab**

---

## 9) Endpoint Reference (Backend)

### OAuth Flow
- **GET** `/api/schwab/oauth/start/` → Returns `{ "auth_url": "..." }`
- **GET** `/api/schwab/oauth/callback/?code=...` → Exchanges code for tokens, stores, returns `{ "success": true }`

### Account Data (requires stored tokens)
- **GET** `/api/schwab/accounts/` → List all Schwab accounts for user. Response mirrors Schwab payload plus `thor_account_id` and `broker_account_id` (hashValue). Account numbers → hashes cached in Redis for 60s.
- **GET** `/api/schwab/account/positions/?account_number=...` → Preferred positions endpoint (account number or hash). Publishes and caches last-good snapshot.
- **GET** `/api/schwab/account/summary/?account_number=...` → Preferred balances summary (account number or hash). Publishes and caches last-good snapshot.
- **GET** `/api/schwab/accounts/<account_id>/positions/` → Legacy positions path (number or hash).
- **GET** `/api/schwab/accounts/<account_id>/balances/` → Legacy balances path (number or hash).

### Frontend routes
- **GET** `/schwab/callback` → React page that handles Schwab redirect and exchanges code

---

## 10) Authentication Notes

### JWT vs Session
- All Schwab endpoints use `@permission_classes([IsAuthenticated])` (DRF JWT auth)
- **NOT** Django session-based `@login_required` (which causes 302 redirects)
- Frontend must include `Authorization: Bearer <access_token>` header
- Api interceptors in `src/services/api.ts` handle token refresh on 401

### Client ID formatting
- **Authorize endpoint** (`oauth_start`): Use raw client_id (no suffix)
  - Example: `1mSMu45mUf2yQwtDaIydOOl7Kyesos95wKMN17JJgsyMuruR`
- **Token endpoint** (`exchange_code_for_tokens`): Append `@AMER.OAUTHAP` suffix
  - Example: `1mSMu45mUf2yQwtDaIydOOl7Kyesos95wKMN17JJgsyMuruR@AMER.OAUTHAP`

---

## 11) Notes for Future Multi-User Support

- Each Thor user should have their own `BrokerConnection` records
- Tokens must be stored per-user (never shared)
- "Paper mode" should be usable without any OAuth
- "Live mode" requires the user to connect their own brokerage via OAuth
- For "quotes without user accounts", use a separate market data provider (not a user's Schwab trading tokens)
