# ThorTrading API

Stateless REST APIs for frontend consumption. Control markets are DB-driven via
GlobalMarkets (see ThorTrading.config.markets:get_control_countries) so the API
always reflects the live enabled markets (session-enabled only).

---

## Core Endpoints

- quotes/latest
- quotes/ribbon
- market-opens/* (latest uses get_control_countries(require_session_capture=True))
- stats & analytics
- manual close capture (override)

---

## API Rules

- No session logic
- No timing logic
- Reads from DB / Redis only
- Control market list is queried at request time; no hard-coded CONTROL_COUNTRIES
