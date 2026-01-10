# Thor environments: production vs dev vs local

This doc is the “map” of which config files matter in each environment, and what they affect.

The main mental model:

- **Backend (Django)** reads env vars at *runtime*.
- **Frontend (Vite/React)** reads `VITE_*` env vars at *build time* (when you run `vite build` / build the Docker image).
- **Vite dev server proxy** is *dev-only* (it does not exist in production).
- **Cloudflared ingress** decides whether a request goes to backend (Django) or frontend (SPA).

---

## Environment matrix

| Environment | Frontend runs as | Backend runs as | How `/api/*` reaches Django | Cloudflare tunnel |
| --- | --- | --- | --- | --- |
| **Local dev** (no Docker backend) | Vite dev server on `:5173` | `python manage.py runserver` on `:8000` | Vite dev proxy `/api` → `:8000` | Optional (`dev-thor`) |
| **Prod-like local** (Docker stack) | Docker `frontend` (NGINX serving `dist/`) or Vite dev | Docker `web` (Gunicorn on `:8000`) behind Docker `nginx` (reverse proxy) | Frontend NGINX proxies `/api` → backend `nginx` → `web:8000` | Optional (`thor-prod`) |
| **Production** (thor.360edu.org) | Docker `frontend` (NGINX) | Docker `web` + `asgi` behind Docker `nginx` | Cloudflared routes `/api` → backend `nginx` | Yes (`thor-prod`) |

---

## Production (Docker + cloudflared)

### Source-of-truth files

- **Docker stack**: `docker-compose.yml`
  - Defines `web` (Gunicorn), `asgi` (Daphne), `nginx` (backend proxy), `frontend` (SPA proxy), `cloudflared`, `postgres`, `redis`.

- **Cloudflare tunnel ingress (production)**: `cloudflared/thor-prod.yml`
  - Routes:
    - `/api/.*`, `/ws/.*`, `/admin/.*`, `/static/.*`, `/media/.*` → backend `nginx`
    - everything else → `frontend`

- **Backend reverse proxy**: `docker/nginx/backend.conf`
  - Proxies Django requests to `web:8000` and WebSockets to `asgi:8001`.
  - Serves `/static/` and `/media/` from Docker volumes.

- **Frontend NGINX**: `docker/nginx/frontend.conf`
  - Serves the compiled React build.
  - Proxies `/api/` to the backend proxy service named `nginx` on the Compose network.

- **Backend env vars**: `.env`
  - Used by `docker-compose.yml` via `env_file: .env` for backend containers.
  - **Important:** `docker-compose.yml` overrides some vars for containers (e.g. `DB_HOST=postgres`, `REDIS_HOST=redis`).

- **Frontend build-time env vars**: `thor-frontend/.env.docker`
  - Must contain `VITE_API_BASE_URL=/api` for production.
  - This is baked into the built JS bundle.

### How it’s supposed to work

- Browser loads `https://thor.360edu.org/auth/login/` from the frontend container.
- Clicking “Activate” should call:
  - `POST https://thor.360edu.org/api/users/login/`
- Cloudflared forwards `/api/...` to backend NGINX which forwards to Django.

### Production commands

- Rebuild frontend and restart (when changing Vite env vars or frontend code):
  - `docker compose build frontend`
  - `docker compose up -d`

- If you change `docker/nginx/*.conf`:
  - `docker compose up -d --build nginx frontend`

---

## Development (dev-thor.360edu.org tunnel)

### Source-of-truth files

- **Cloudflare tunnel ingress (dev)**: `cloudflared/thor-dev.yml`
  - Routes backend paths (`/api`, `/admin`, `/ws`, static/media) to your local Django port.
  - Routes everything else to the local Vite dev server (`:5173`).

- **Frontend dev server config**: `thor-frontend/vite.config.ts`
  - Defines the dev-only proxies:
    - `/api` → `PROXY_TARGET`
    - `/ws` → `PROXY_TARGET` converted to `ws://...`

- **Tunnel-friendly HMR**: frontend script `npm run dev:tunnel`
  - Sets `VITE_HMR_HOST`, `VITE_HMR_PROTOCOL`, `VITE_HMR_CLIENT_PORT` so HMR works over HTTPS.

### Typical dev commands

- Start Postgres + Redis in Docker:
  - `docker compose up -d postgres redis`

- Start backend locally:
  - `cd thor-backend`
  - `python manage.py runserver`

- Start frontend locally:
  - `cd thor-frontend`
  - `npm run dev:local`

- Optional: run dev tunnel:
  - `cloudflared tunnel run dev-thor`

---

## Local-only (no external tunnel)

### Backend env vars

- `.env` is also used for local backend runs.
  - Local backend expects `DB_HOST=localhost` and `REDIS_URL=redis://localhost:6379/0` (which matches `.env`).

### Frontend local env vars

- `thor-frontend/.env.local` is the local dev override.
  - Example: `VITE_API_BASE_URL=http://127.0.0.1:8000/api` (direct to local backend)

---

## Frontend environment files (important)

### What each file means

- `thor-frontend/.env.local`
  - **Local dev override**.
  - Vite loads this file for all modes.
  - If this contains localhost URLs, and it leaks into a Docker build, production will break.

- `thor-frontend/.env.docker`
  - Template for Docker/prod-like behavior.
  - Should use `VITE_API_BASE_URL=/api`.

- `thor-frontend/scripts/switch-env.mjs`
  - Used by `npm run dev:docker` to copy `.env.docker` → `.env.local`.
  - This is convenient, but it can surprise you if you expect `.env.local` to stay “local-only”.

### Build-time gotcha (the one that bit us)

Vite reads `VITE_*` at build time. If you build the Docker image while `.env.local` contains `http://127.0.0.1:8000/api`, that string gets baked into the JS.

Guard rails in this repo:

- Frontend Docker build runs: `npm run build -- --mode docker` so `.env.docker` is used.
- Root `.dockerignore` excludes `**/.env.local` so it can’t get copied into Docker build contexts.

---

## Cloudflare tunnel files

- `cloudflared/thor-prod.yml`
  - Production routing (Docker services inside the Compose network).

- `cloudflared/thor-dev.yml`
  - Dev routing (services on your Windows host).

Key rule: **backend routes must be listed before the catch-all frontend rule**, otherwise `/api/*` and `/ws/*` will get sent to the SPA.

---

## NGINX files

- Backend proxy:
  - `docker/nginx/backend.conf` (used by the `nginx` Compose service)
  - `docker/nginx/nginx.conf` (legacy reference)

- Frontend proxy:
  - `docker/nginx/frontend.conf` (baked into the `frontend` image)

Also see: `docker/nginx/NGINX.md` (great operational summary).

---

## Quick diagnostics checklist

When login fails in prod, verify these in order:

1. In the browser Network tab, the login request should be:
   - `POST https://thor.360edu.org/api/users/login/`
2. If you see `localhost` or `127.0.0.1` in the request URL:
   - The frontend bundle was built with a local `VITE_API_BASE_URL`.
   - Rebuild the frontend Docker image.
3. If you see `POST https://thor.360edu.org/login/` (missing `/api`):
   - The frontend is not using the API base URL / the request is not going through the API client.
4. If `/auth/login/` loads but `/api/...` fails:
   - Cloudflared ingress rules are misrouted (or the backend proxy is down).

---

## Suggested conventions (to prevent repeats)

- Keep **localhost URLs only** in `.env.local`.
- Keep **production-safe defaults** in `.env.docker` (relative `/api`).
- Always rebuild frontend images when changing any `VITE_*` values.
