![ is this correct
]({D0A5AB28-6635-4E5A-85BF-8EC5B536E7D3}.png)# Cloudflare Tunnel for Thor (plan for next week)

This guide wires thor.360edu.org to your local Django dev server (port 8000) using Cloudflare Tunnel. No app changes are required right now; this is a ready-to-run plan for later.

Note: Our app already supports root-level OAuth callback routes at `/auth/callback` and `/schwab/callback`, and the Schwab login endpoint is `/api/schwab/auth/login/`. We’ll point the Schwab portal to the tunnel host when you’re ready.

---

## A) One-time Cloudflare setup (Free plan)

1) Add the domain to Cloudflare (Free plan)
- Add `360edu.org` in the Cloudflare dashboard.
- Update nameservers at Network Solutions to the two nameservers Cloudflare provides.
- Wait until the domain shows Active in Cloudflare.

We will use `thor.360edu.org` for the backend tunnel. Your main site remains unchanged.

---

## B) Install and authenticate cloudflared (Windows)

Open PowerShell and either install via Chocolatey or download the exe to PATH.

```powershell
# Install with Chocolatey
choco install cloudflared -y

# Or download cloudflared.exe and add it to PATH
```

Authenticate cloudflared with your Cloudflare account:

```powershell
cloudflared tunnel login
```

This opens the browser; pick your Cloudflare account and zone (`360edu.org`).

---

## Step 1 — Confirm the correct binary and service path (Windows)

Goal: Ensure the cloudflared binary on PATH matches the Windows service binary, and that the service uses the expected config/credentials.

- Expected binary path (verified on this machine):
  - C:\Program Files (x86)\cloudflared\cloudflared.exe
- Windows Service (verified):
  - Name: cloudflared
  - DisplayName: Cloudflared agent
  - StartType: Automatic
  - BinaryPath (ImagePath): C:\Program Files (x86)\cloudflared\cloudflared.exe
- Service config and credentials (verified):
  - Config: C:\ProgramData\cloudflared\config.yml
  - Credentials file: C:\ProgramData\cloudflared\<TUNNEL-UUID>.json
- User profile config (optional, used for foreground runs):
  - Config: %USERPROFILE%\.cloudflared\config.yml
  - Credentials file: %USERPROFILE%\.cloudflared\<TUNNEL-UUID>.json

Quick checks you can run in PowerShell:

```powershell
# 1) Confirm the resolved binary on PATH
where.exe cloudflared
Get-Command cloudflared | Select-Object -Property Path

# 2) Confirm the Windows service and its binary path
Get-Service cloudflared | Format-Table Name,DisplayName,Status,StartType
sc.exe qc cloudflared
reg query "HKLM\SYSTEM\CurrentControlSet\Services\cloudflared" /v ImagePath

# 3) Confirm service config and credentials exist
Test-Path "C:\ProgramData\cloudflared\config.yml"
Get-ChildItem "C:\ProgramData\cloudflared" | Format-Table Name,FullName,Length

# 4) Confirm the tunnel is present
cloudflared tunnel list
```

What “good” looks like:
- The resolved binary path(s) output only C:\Program Files (x86)\cloudflared\cloudflared.exe.
- The service exists, is Automatic start, and ImagePath matches the same binary.
- C:\ProgramData\cloudflared\config.yml exists and references a credentials-file that also exists in the same folder.
- `cloudflared tunnel list` shows your tunnel (e.g., `thor`) and a UUID.

If something’s off:
- Multiple binaries found: remove stale copies from PATH or prefer the full path in scripts.
- Service missing config/creds in ProgramData: copy your user profile credentials JSON to ProgramData and point config.yml to it, or re-run `cloudflared service install`.
- Service running but stuck (e.g., StopPending): try `Restart-Service cloudflared` and check Windows Event Viewer > Application logs for cloudflared.

Once these checks pass, proceed to create/route the tunnel below.

---

## C) Create the tunnel and DNS route

Create a named tunnel (Cloudflare returns a UUID and writes a credentials JSON file under %USERPROFILE%\.cloudflared):

```powershell
cloudflared tunnel create thor-local
```

Route the subdomain to the tunnel:

```powershell
cloudflared tunnel route dns thor-local thor.360edu.org
```

---

## D) Configure the tunnel to proxy Django (localhost:8000)

Create `%USERPROFILE%\.cloudflared\config.yml` with:

```yaml
tunnel: thor-local
credentials-file: C:\Users\<YourWindowsUser>\.cloudflared\<YOUR-UUID>.json

ingress:
  - hostname: thor.360edu.org
    service: http://localhost:8000
  - service: http_status:404
```

Replace `<YourWindowsUser>` and `<YOUR-UUID>` with your actual values from step C.

---

## E) Run the tunnel

Keep it running while you develop, or install as a service so it auto-starts.

```powershell
# Foreground run (good for testing)
cloudflared tunnel run thor-local

# Optional: install as a Windows service
# cloudflared service install
# cloudflared tunnel run thor-local
```

---

## F) Point Schwab and the app to the new HTTPS callback

In the Schwab Developer Portal (Thor Trading app), add the callback URL:

```
https://thor.360edu.org/schwab/callback
```

Also keep your existing production callback if applicable.

Update your local `.env` for development. Prefer using the dev override so production stays unchanged:

```
SCHWAB_REDIRECT_URI=https://360edu.org/auth/callback                    # production
SCHWAB_REDIRECT_URI_DEV=https://thor.360edu.org/schwab/callback        # dev via Cloudflare
```

Restart Django so the new env values are picked up.

Routes that must exist (already implemented):

---

## G) Verification checklist and URLs

Public domain via Cloudflare Tunnel:
- https://thor.360edu.org

Backend base (through tunnel):
- https://thor.360edu.org/api/

Schwab OAuth endpoints:
- Start login (local): http://localhost:8000/api/schwab/auth/login/
- Start login (through tunnel): https://thor.360edu.org/api/schwab/auth/login/
- OAuth callback (root): https://thor.360edu.org/schwab/callback
- OAuth callback (app): https://thor.360edu.org/api/schwab/auth/callback

Provider diagnostics:
- Health: https://thor.360edu.org/api/schwab/provider/health/?provider=schwab
- Status: https://thor.360edu.org/api/schwab/provider/status/?provider=schwab
- Debug GET: https://thor.360edu.org/api/schwab/debug/get/?path=/v1/accounts

What to enter in Schwab Developer Portal:
- Redirect URI: https://thor.360edu.org/schwab/callback

Quick tests:
1) Start Django locally on port 8000.
2) Visit Health: https://thor.360edu.org/api/schwab/provider/health/?provider=schwab (auth.configured should be true when .env is set)
3) Start OAuth: https://thor.360edu.org/api/schwab/auth/login/ (should redirect to Schwab)
4) Complete consent and verify callback to https://thor.360edu.org/schwab/callback exchanges code for tokens.

## G) Test the full OAuth flow

1) Start Django on port 8000.
2) Ensure `cloudflared tunnel run thor-local` is running.
3) Visit:

- Start login locally: `http://127.0.0.1:8000/api/schwab/auth/login/`
- After Schwab approval, you should land on `https://thor.360edu.org/schwab/callback` (Cloudflare terminates TLS and forwards to localhost), and the app will exchange the `code` for tokens.

Useful verification endpoints:
- Provider status: `http://127.0.0.1:8000/api/schwab/provider/status/?provider=schwab`
- Debug raw GET: `http://127.0.0.1:8000/api/schwab/debug/get/?path=/v1/accounts`

---

## Notes and safety

- If a Schwab client secret was previously exposed, regenerate it in the portal and update `.env`.
- Ensure `.env` stays out of Git (it’s in `.gitignore`).
- Windows Firewall can remain on; Cloudflare Tunnel uses outbound connections only.
- If you later deploy the backend, you can keep `thor.360edu.org` and repoint the tunnel/DNS to that server instead of localhost.
- For non-DEBUG environments, add `thor.360edu.org` to Django `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` (or use an env-driven allowlist).

---

## Auto-Recovery (Windows Service)

If Cloudflared crashes or is terminated, configure Windows Service recovery to auto-restart.

Option A — Run the helper script (elevates automatically):

```powershell
./scripts/configure_cloudflared_recovery.ps1
```

Option B — Run commands manually (PowerShell as Administrator):

```powershell
sc.exe failure cloudflared reset= 86400 actions= restart/5000/restart/10000/""/15000
sc.exe failureflag cloudflared 1
```

Verify settings:

```powershell
sc.exe qfailure cloudflared
```

✅ Why: Auto-restarts after 5 s and again after 10 s; resets the counter every 24 h. OK proceed.

---

## Do not implement yet

This document is a plan for next week. We are not changing the app right now. If desired later, we can also add convenience routes like `/schwab/login` and `/schwab/accounts`, but the current endpoints already support the full OAuth flow and testing.
