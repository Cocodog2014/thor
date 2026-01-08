GlobalMarkets (Backend)
Purpose

GlobalMarkets is a lightweight backend service that tracks when markets open and close across time zones.

It is not a price engine, not a streaming service, and not a heartbeat system.

Its only responsibilities are:

Define markets and their schedules (Admin-managed)

Compute market status (OPEN / PREMARKET / CLOSED)

Persist status only when it changes

Emit events only when status changes

Let the frontend handle clocks and ticking

Core Design Principles
1. No Heartbeats

There is no per-second loop and no cron-style job stack.

The system:

Computes the next known transition

Sleeps until something is expected to change

Wakes up only when necessary

This eliminates:

constant DB writes

constant WebSocket broadcasts

Redis churn

frontend freezes

2. Transition-Only Writes

The database is not a live clock.

Market.status is updated only when a transition occurs:

CLOSED → PREMARKET

PREMARKET → OPEN

OPEN → CLOSED

If nothing changes, nothing is written.

3. Transition-Only Broadcasts

WebSocket or event broadcasts happen only when status changes.

The frontend:

Receives a single event

Starts its own local timer

Renders clocks without backend involvement

4. Admin Is the Source of Truth

All configuration lives in the database and is editable via Django Admin.

No hardcoded markets.
No hardcoded holidays.
No hardcoded weekends.

Data Model (3 Models Only)
Market

Represents a single global market clock.

Fields include:

key – stable identifier (used by frontend & events)

name

timezone_name (IANA timezone)

status (persisted state)

status_changed_at

is_active

sort_order

This model does not contain schedule or holiday rules.

MarketSession

Defines weekly trading hours for a market.

One row per weekday (0=Mon … 6=Sun)

Supports:

closed days

premarket

regular open

close

This replaces hardcoded “weekend” logic entirely.

MarketHoliday

Defines date-specific exceptions.

Supports:

Full-day closures

Early closes

Holidays are owned by the Market directly — no shared calendar abstraction.

Status Computation

Status is computed using:

Market timezone

Today’s MarketHoliday (if any)

Today’s MarketSession

Current local time

Possible statuses:

CLOSED

PREMARKET

OPEN

The computation lives entirely in:

GlobalMarkets/services.py


This file is the single source of truth for market state.

Runner (The Only Background Process)
Management Command
python manage.py run_markets

What it does

Loads all active markets

Computes current status

Detects transitions

Saves status only if changed

Emits signals and broadcasts

Sleeps until the next transition

What it does NOT do

No heartbeat

No polling every second

No Redis caching loop

No continuous WebSocket spam

Signals & Decoupling

GlobalMarkets emits signals when status changes:

market_status_changed

market_opened

market_closed

Other apps (futures, capture engines, analytics) may listen to these without GlobalMarkets knowing about them.

GlobalMarkets itself:

never triggers capture

never triggers trading logic

never references downstream systems

Frontend Contract

The backend:

tells the frontend when a market opened or closed

provides timezone + schedule metadata

The frontend:

handles ticking clocks

handles countdowns

handles UI refreshes

This separation keeps both sides simple and performant.

File Count Philosophy

The entire GlobalMarkets backend is intentionally kept to 10 files or fewer.

There is:

no DRF viewset jungle

no job registry

no layered heartbeat system

no duplicate status logic

Every file has a single, clear responsibility.

Summary

GlobalMarkets is intentionally boring.

That’s the point.

It answers one question reliably:

Is this market open right now — and when will that change?

Everything else belongs somewhere else.