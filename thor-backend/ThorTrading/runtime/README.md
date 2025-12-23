# ThorTrading Runtime

This folder contains **runtime enforcement and safety controls** for ThorTrading.

It exists to ensure that **only the approved execution model** is allowed
to run in a given environment.

If something in this folder is firing, it means the system is **protecting
itself from legacy or invalid execution paths**.

---

## Purpose

The runtime layer enforces these rules:

- ThorTrading must be driven by a **single global heartbeat**
- Legacy thread-based schedulers must NOT be reactivated
- Background workers must not free-run outside approved control flow
- Environment configuration must match the expected scheduler mode

This folder does **not** contain business logic.
It contains **guardrails**.

---

## Scheduler Model (Authoritative)

ThorTrading runs in **heartbeat mode only**.

- One heartbeat
- One scheduler
- One source of timing truth

Any attempt to run legacy schedulers or ad-hoc loops
is considered a configuration error.

---

## Runtime Guards

Runtime guards are defensive checks that **fail fast** if the system is misconfigured.

### Example: Scheduler Guard

`guards.py` enforces that the legacy scheduler cannot be enabled
in environments where the heartbeat scheduler is required.

If `THOR_SCHEDULER_MODE` is set incorrectly, the process will raise immediately
instead of silently running duplicate schedulers. :contentReference[oaicite:0]{index=0}

This prevents:
- Double timers
- Competing worker loops
- Drift between services
- Hard-to-debug race conditions

---

## What Belongs
