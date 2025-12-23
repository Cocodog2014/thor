# Realtime & Heartbeat

ThorTrading uses a **single global heartbeat**.

---

## Responsibilities

- Scheduler registration
- WebSocket broadcasting
- Worker coordination

---

## Rules

- One heartbeat only
- No per-service timers
