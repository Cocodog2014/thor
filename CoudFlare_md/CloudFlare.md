🌐 Cloudflare Tunnel — Thor Development Guide (Final Master Document)

This document explains exactly how Thor uses Cloudflare Tunnel in development, how to start it, how routing works, and how to recover your configuration instantly.
Cloudflare Tunnel provides HTTPS access to your local computer — nothing here is hosted or deployed on Cloudflare servers.

⚡ 1. What the Tunnel Does

When the tunnel is running, the domains https://thor.360edu.org
and https://dev-thor.360edu.org securely forward requests to your local machine:

URL Path	Local Service	Description
/	localhost:5173	React (Vite) frontend
/admin/	localhost:8000	Django Admin Panel
/api/	localhost:8000	Django API endpoints
/static/	localhost:8000	Django static files
/media/	localhost:8000	Django media files

Cloudflare handles HTTPS
Your PC handles the actual application

This allows full Schwab OAuth testing, API calls, and local dev — all through a real, secure domain.

⚙️ 2. The Cloudflare Config File

Cloudflare Tunnel uses:

C:\Users\sutto\.cloudflared\config.yml


This file contains your routing rules. Here is the correct version (backed up in your MD folder and kept in sync with both tunnel hostnames):


Backup(.cloudflared)

tunnel: thor
credentials-file: C:\Users\sutto\.cloudflared\556698d2-2814-415f-a31e-4c3c49c1e120.json

ingress:
  # Ensure TS/JS modules load from Vite on both domains
  - hostname: thor.360edu.org
    path: /src/*
    service: http://localhost:5173
  - hostname: dev-thor.360edu.org
    path: /src/*
    service: http://localhost:5173

  # Django backend (admin, API, static/media)
  - hostname: thor.360edu.org
    path: /admin/*
    service: http://localhost:8000
  - hostname: thor.360edu.org
    path: /admin
    service: http://localhost:8000
  - hostname: thor.360edu.org
    path: /api/*
    service: http://localhost:8000
  - hostname: thor.360edu.org
    path: /static/*
    service: http://localhost:8000
  - hostname: thor.360edu.org
    path: /media/*
    service: http://localhost:8000
  - hostname: dev-thor.360edu.org
    path: /admin/*
    service: http://localhost:8000
  - hostname: dev-thor.360edu.org
    path: /admin
    service: http://localhost:8000
  - hostname: dev-thor.360edu.org
    path: /api/*
    service: http://localhost:8000
  - hostname: dev-thor.360edu.org
    path: /static/*
    service: http://localhost:8000
  - hostname: dev-thor.360edu.org
    path: /media/*
    service: http://localhost:8000

  # Everything else → React dev server on 5173
  - hostname: thor.360edu.org
    service: http://localhost:5173
  - hostname: dev-thor.360edu.org
    service: http://localhost:5173

  # Catch-all
  - service: http_status:404


This config ensures perfect separation:

Frontend traffic → Vite (both thor/dev-thor domains)

API & admin traffic → Django

🔁 Dev domain reminder: `.env.local` must keep `VITE_API_BASE_URL=/api` so the browser sends requests to the same hostname it loaded from (Cloudflare rewrites /api → localhost:8000).

📁 3. What’s in the /CloudFlareMD Folder?

This folder holds all documentation and backup configs related to Cloudflare Tunnel:

CloudFlareConfigUpdateYML

CloudflareTunnel.md (this document)

CLOUDFLARE_SETUP_COMPLETE.md

RESTART_CLOUDFLARED.md

SUCCESS_CLOUDFLARE_WORKING.md

These are developer reference files, not used by Cloudflare itself.

🔍 Why this folder exists

To keep all Cloudflare knowledge in one place

To avoid losing the correct config.yml

To let any developer restore or understand the tunnel fast

To ensure consistency if Windows or Cloudflare overwrites files

📄 4. What Is CloudFlareConfigUpdateYML?

CloudFlareConfigUpdateYML is your reference copy of the working Cloudflare config.yml.

It is:

Not used directly by Cloudflare

Not read when the tunnel runs

Only for you (developer backup + restore)

Why it exists

Windows, Cloudflare updates, or service reinstalls sometimes overwrite:

C:\Users\sutto\.cloudflared\config.yml


If that happens, simply:

How to restore the tunnel config

Open CloudFlareConfigUpdateYML

Copy contents

Paste into:

C:\Users\sutto\.cloudflared\config.yml


Restart Cloudflare:

cloudflared tunnel run thor


Instant recovery — no debugging.

🧩 5. STARTUP GUIDE — Run Thor Through Cloudflare

(3-terminal workflow)

Terminal 1 — Start Django Backend
cd A:\Thor\thor-backend
python manage.py runserver 0.0.0.0:8000

Terminal 2 — Start React Frontend
cd A:\Thor\thor-frontend
npm run dev:local

Terminal 3 — Start Cloudflare Tunnel
cloudflared tunnel run thor


👉 This terminal must stay open.
Closing it turns off the tunnel.

🧪 6. Testing That Everything Works
✔️ Frontend (React)

https://thor.360edu.org/  or  https://dev-thor.360edu.org/

→ Should show Thor login screen (same instance)

✔️ Django Admin

https://thor.360edu.org/admin/  or  https://dev-thor.360edu.org/admin/

✔️ API Root

https://thor.360edu.org/api/  (dev-thor equivalent works too)

✔️ Local fallback (always available)

http://localhost:5173
 (frontend)

http://localhost:8000
 (backend)

🔁 7. Restarting Cloudflare Tunnel (If Something Breaks)

If you modify the config or Cloudflare hangs:

Stop the tunnel
Get-Process cloudflared | Stop-Process -Force

Restart it
cloudflared tunnel run thor


This restart process is also documented in:


RESTART_CLOUDFLARED

🔍 8. Troubleshooting Quick Guide
❌ Frontend not loading

Check Vite:

Get-Process node


Restart:

cd A:\Thor\thor-frontend
npm run dev:local

❌ Admin/API failing

Check Django:

Get-Process python


Restart:

python manage.py runserver

❌ Wrong routing / white screen

Likely config.yml overwritten → Restore from CloudFlareConfigUpdateYML.

❌ Tunnel running but domain not loading

Restart Cloudflare:

Get-Process cloudflared | Stop-Process -Force
cloudflared tunnel run thor

🎉 9. Summary — Your Final Cloudflare Workflow

Thor is NOT hosted on Cloudflare

Cloudflare Tunnel simply forwards traffic → your dev machine

The tunnel enables full HTTPS, OAuth, and API testing

Your /CloudFlareMD folder keeps everything documented and backed up

You start 3 terminals → Django, Vite, Cloudflare

You now have professional, rock-solid dev URLs:
https://thor.360edu.org and https://dev-thor.360edu.org

