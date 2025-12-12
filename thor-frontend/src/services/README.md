# Services Module Overview

This folder contains the shared HTTP clients used across the Thor frontend.

## api.ts

- Creates a preconfigured Axios instance whose `baseURL` adapts to local dev, Cloudflare tunnels, or Docker environments.
- Handles public vs. authenticated endpoints. Public endpoints (e.g., `/global-markets/markets`, `/quotes`, `/vwap`) automatically strip any `Authorization` header.
- Token lifecycle is coordinated with `AuthContext` via `setAuthHeader(token)`:
  - AuthContext sets or clears the default `Authorization` header whenever users log in/out.
  - The response interceptor refreshes access tokens using `/users/token/refresh/` when it receives a 401 and removes all tokens (plus redirects to `/auth/login`) if refresh fails.
- Any module needing authenticated API calls should import the default export (`api`) rather than creating new Axios instances.

## markets.ts

- Provides higher-level helpers for market-related data (e.g., fetch global markets, quotes, VWAP data).
- Each helper wraps `api` so they benefit from the shared headers, interceptors, and error handling.
- Use these functions in components/pages instead of duplicating endpoint logic.

Keep this file updated whenever services change (new helpers, new base URLs, etc.).
