# NGINX Guide

This note lives next to the reverse-proxy configs so anyone can see how both NGINX layers are wired inside the Docker stack and what to touch when something breaks.

## Containers at a Glance

| Role | Compose Service → Container | Image Source | Host Port | Config File |
| --- | --- | --- | --- | --- |
| Backend reverse proxy for Django + static/media | `nginx` → `thor_nginx` | `nginx:alpine` (stock) | `8001:80` | [docker/nginx/backend.conf](backend.conf) |
| Frontend SPA proxy + `/api` bridge | `frontend` → `thor_frontend` | Multi-stage build ending in `nginx:alpine` | `8080:80` | [docker/nginx/frontend.conf](frontend.conf) |

Both services ultimately run NGINX but have different jobs: the backend proxy terminates requests for Gunicorn and static assets, while the frontend proxy serves the compiled React bundle and forwards API calls to the backend.

## Backend Proxy (`thor_nginx`)
- Uses [docker/nginx/backend.conf](backend.conf) (and the legacy copy [docker/nginx/nginx.conf](nginx.conf) kept for reference).
- Talks to `thor_web` (Gunicorn) over the Compose network via the `upstream thor_web { server web:8000; }` block.
- Serves `/static/` and `/media/` directly from the shared Docker volumes `static_volume` and `media_volume` so Gunicorn never touches large assets.
- Exposes a simple health probe at `/nginx-health` used by `curl http://localhost:8001/nginx-health` or Cloudflare.
- Config is mounted read-only by [docker-compose.yml](../../docker-compose.yml#L63-L82); edits require `docker compose restart nginx`.

## Frontend Proxy (`thor_frontend`)
- Built via [thor-frontend/Dockerfile](../../thor-frontend/Dockerfile): Node stage builds `dist/`, runtime stage copies it into an `nginx:alpine` image, and [docker/nginx/frontend.conf](frontend.conf) becomes `/etc/nginx/conf.d/default.conf`.
- Serves the React SPA at `http://localhost:8080/` (or through Cloudflare) with hashed assets cached aggressively under `/assets/`.
- Bridges API calls by proxying `/api/` to the backend proxy (`proxy_pass http://nginx;`), so browsers never call Gunicorn directly.
- Ships its own `/healthz` endpoint for lightweight uptime checks.

## Request Flow

```
Browser → thor_frontend (8080)
  • /assets/* served from /usr/share/nginx/html
  • /api/* proxied to thor_nginx (8001)
      ↳ thor_nginx → thor_web (Gunicorn 8000) → Django
  • /static + /media handled only by thor_nginx
```

## Operations Cheat Sheet

| Task | Command |
| --- | --- |
| Rebuild everything (configs changed) | `docker compose up -d --build nginx frontend` |
| Restart just one proxy | `docker compose restart nginx` or `docker compose restart frontend` |
| Tail logs | `docker compose logs -f nginx` or `docker compose logs -f frontend` |
| Hit health checks | `Invoke-WebRequest http://localhost:8001/nginx-health` and `Invoke-WebRequest http://localhost:8080/healthz` |

## Editing Tips

1. Update the relevant `.conf` file in this folder.
2. Rebuild/restart the matching service so the container picks up the change.
3. Validate syntax before restart with `docker run --rm -v ${PWD}/docker/nginx:/etc/nginx/conf.d nginx:alpine nginx -t` (optional but fast).
4. Keep cache headers in sync with frontend build outputs—hashed bundles can use year-long caching, everything else should remain short-lived.

## Troubleshooting

- **Frontend loads but API 502s:** Ensure the `nginx` service is running and port `8001` responds. Inside the Compose network the hostname is literally `nginx`, so if you rename the service update `proxy_pass` accordingly.
- **Static files 404 via backend:** Check that `static_volume`/`media_volume` are populated. Run `docker compose exec web python manage.py collectstatic` if needed.
- **Cloudflare tunnel mismatch:** Remember tunnels hitting the SPA must expose both `8080` (frontend) and `8001` (backend) if you plan to access the Django admin directly; otherwise `/api` traffic will die when the frontend proxy can’t reach the backend port.
- **Single container showing up in Docker Desktop:** That list is per-service. Even though `thor_frontend` shows up with a custom image name, it is still an NGINX container because the runtime stage is `FROM nginx:alpine`.

Keep this file close to the configs so future edits or onboarding questions about NGINX have a canonical answer.
