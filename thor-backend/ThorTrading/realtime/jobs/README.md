# ThorTrading Heartbeat Jobs

This folder contains **all ThorTrading heartbeat jobs**.

Each job is a **small, deterministic unit of work** that runs under the
**single global heartbeat scheduler**.

There are **no standalone loops**, no timers, and no background threads
inside these jobs.

---

## Execution Model (Authoritative)

- All jobs run under **one global heartbeat**
- Jobs are registered once at startup
- Each job controls its own cadence via `interval_seconds`
- The heartbeat decides *when* a job may run
- Jobs decide *whether* they should run

There are no per-job schedulers.

---

## Job Registration

All ThorTrading jobs are registered centrally via the provider.

**File:**
