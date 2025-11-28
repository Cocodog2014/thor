# Canonical Seed Data

Human-readable tables for constants that should live in Git and be mirrored by machine-readable fixtures.

## Control Markets (Global Clock)

| Code | Name | Timezone | Open (local) | Close (local) | Weight | Enabled |
|------|------|----------|--------------|---------------|--------|---------|
| JP   | Japan | Asia/Tokyo | 09:00 | 15:00 | 10 | true |
| CN   | China | Asia/Shanghai | 09:30 | 15:00 | 10 | true |
| IN   | India | Asia/Kolkata | 09:15 | 15:30 | 10 | true |
| DE   | Germany | Europe/Berlin | 09:00 | 17:30 | 10 | false |
| UK   | United Kingdom | Europe/London | 08:00 | 16:30 | 10 | true |
| PRE  | Pre-USA | America/New_York | 06:00 | 09:30 | 10 | true |
| US   | USA | America/New_York | 09:30 | 16:00 | 20 | true |
| CA   | Canada | America/Toronto | 09:30 | 16:00 | 10 | false |
| MX   | Mexico | America/Mexico_City | 08:30 | 15:00 | 10 | false |

## Futures Universe

`TOTAL`, `YM`, `ES`, `NQ`, `RTY`, `CL`, `SI`, `HG`, `GC`, `VX`, `DX`, `ZB`

## Seed Files (machine-readable)

Place JSON/YAML fixtures under `thor-backend/data/` and wire a `manage.py thor_seed_all` command to load them:

- `seed_markets.json`: control markets + schedules + flags + weights
- `seed_futures.json`: futures symbols + display names
- `seed_default_weights.json`: TOTAL composition weights
- `seed_users.json` (optional): initial admin/dev accounts

This doc is the canonical spec; fixtures and commands must match it.
