# ngrok + Schwab OAuth: Verify the pipeline

This page shows exactly how to confirm your Schwab OAuth tunnel is working and how to test data calls through the Thor backend.

## Prereqs

- Backend running on http://127.0.0.1:8000
- ngrok tunnel running and portal/.env updated (see START.md Step 4)
- OAuth completed at least once so tokens are saved
  - Check status: http://localhost:8000/api/schwab/provider/status/?provider=schwab
  - Expect: `tokens.present: true` and `connected: true`

If NOT connected yet:
- Run the ngrok + callback steps in START.md Step 4
- Approve the login
- Recheck status page until tokens.present: true and connected: true

---

## Test 1 — Sanity GET with a path

Call a Schwab API path via Thor using the stored token:

- http://localhost:8000/api/schwab/debug/get/?path=/v1/accounts

You’ll get JSON like:
- `url` (full URL called)
- `status_code` (e.g., 200, 401, 403, etc.)
- `ok` (true/false)
- `text_snippet` (first ~2KB of the response body)

## Test 2 — Full URL

If Schwab docs provide a full URL, you can pass it directly:

- http://localhost:8000/api/schwab/debug/get/?path=https://api.schwabapi.com/v1/accounts

---

## How to interpret results

- 200/201 → Token is valid and the endpoint is reachable: the pipeline is good.
- 401 Unauthorized → Token missing/expired; redo the auth flow to refresh tokens.
- 403 Forbidden → Token OK but missing permissions/entitlements for that endpoint.
- 404 Not Found → Wrong path; double-check the Schwab API path.
- 5xx → Provider-side or transient issue; retry or try a simpler endpoint.

---

## Troubleshooting quick checks

- Status page:
  - http://localhost:8000/api/schwab/provider/status/?provider=schwab
  - Confirm `base_url`, `scopes`, `tokens.present`, `tokens.expired`.

- Callback reachability (should return `{ "error": "missing code" }` when hit directly):
  - https://<your-ngrok-host>/auth/callback
  - or https://<your-ngrok-host>/schwab/callback

- Host/CSRF settings (dev only):
  - ALLOWED_HOSTS accepts `.ngrok-free.app` and `.ngrok-free.dev` when DEBUG=True
  - CSRF_TRUSTED_ORIGINS includes the same; restart Django after edits

- URL must match EXACTLY in both places:
  - Schwab Developer Portal → Callback URL = `https://<ngrok>/auth/callback` (or `/schwab/callback`)
  - A:\\Thor\\thor-backend\\.env → `SCHWAB_REDIRECT_URI_DEV=https://<ngrok>/auth/callback`

---

## Notes

- The `debug/get` endpoint is read-only and meant for diagnostics.
- Once you can reach a real Schwab endpoint successfully, we can wire that endpoint into the provider so the frontend can consume live data.
- For a stable dev URL, use an ngrok reserved domain or Cloudflare Tunnel on a dev subdomain.
