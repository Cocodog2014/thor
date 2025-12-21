GlobalTimerIntegration – ThorTrading + GlobalMarkets

Last updated: December 2025

0. Scope & Intent

This document describes how to integrate ThorTrading with the GlobalMarkets “clock” and session scheduler, so that:

GlobalMarkets is the single source of truth for:

When markets are open / closed

Session boundaries (open → close → next open)

ThorTrading workers (intraday, grading, VWAP, 52-week, etc.) are started/stopped by GlobalMarkets, instead of free-running.

The ThorTrading frontend (futures dashboard) refreshes data using a shared global timer, consistent with the GlobalMarkets banner.

This doc only covers ThorTrading integration (backend + frontend).
GlobalMarkets itself is already defined in its own GlobalMarkets.md.

1. Goals
1.1 Functional Goals

Session ownership

GlobalMarkets decides when a given market (e.g., USA, Pre_USA) is open/closed.

ThorTrading does not compute its own session boundaries.

Worker orchestration

ThorTrading background services (MarketOpen capture, MarketGrader, intraday metrics, VWAP, 52-week supervisor) are controlled by GlobalMarkets signals.

No independent “mystery” loops that ignore open/close.

Consistent frontend timing

ThorTrading React pages refresh at intervals driven by a shared GlobalTimerProvider.

Same heartbeat used by GlobalMarkets TSX component and ThorTrading UI.

1.2 Non-Goals (for now)

No immediate WebSockets / push; we remain poll-based on the frontend.

No major schema changes to ThorTrading models.

No removal of emergency/manual endpoints (e.g., manual close capture).

2. Current State Summary (ThorTrading + GlobalMarkets)
2.1 GlobalMarkets (short)

Market model holds:

country, timezone, open/close config

status (OPEN, CLOSED, etc.)

helpers like get_current_market_time() and is_market_open_now()

Scheduler (monitor.py / management command):

Computes next open/close for each Market

Flips Market.status at those times

Fires signals:

market_status_changed

market_opened

market_closed

2.2 ThorTrading (short)

App startup (apps.ThorTradingConfig.ready):

Starts a delayed thread which calls start_thor_background_stack().

Supervisors / loops (examples):

MarketGrader.run_grading_loop() – 0.5s infinite loop

Intraday supervisor – 1s loop

VWAP minute capturer – 60s loop

52-week supervisor – its own loop

Market open capture supervisor – its own loop

Open/Close:

Market open capture via MarketOpenCaptureService.capture_market_open(market).

Market close metrics via MarketCloseCaptureView (HTTP GET) – manual or script-driven.

A 52-week supervisor already checks GlobalMarkets to decide whether to run, but its internal heartbeat is still independent.

Result: Multiple unsynchronized loops, no single owner for timing, and GlobalMarkets is only partially involved.

3. Integration Design Overview

We introduce two integration layers:

Backend orchestration layer
A set of signal receivers + service hooks that drive ThorTrading workers based on GlobalMarkets’ market_opened / market_closed signals.

Frontend global timer layer
A React GlobalTimerProvider that provides a 1-second heartbeat and GlobalMarkets status, which ThorTrading pages consume for polling / UI timing.

4. Backend Integration Plan
4.1 High-Level Behavior

For each relevant market (primarily Pre_USA and USA):

When GlobalMarkets sets a market to OPEN and fires market_opened:

Capture market-open snapshot for that market via ThorTrading.

Start or resume ThorTrading workers that are supposed to run during this session (grading, intraday, VWAP, 52-week, etc.).

When GlobalMarkets sets a market to CLOSED and fires market_closed:

Finalize close metrics for that country/session.

Stop or pause the relevant ThorTrading workers.

This ensures that session boundaries & worker lifetimes are defined by GlobalMarkets, not by individual ThorTrading loops.

4.2 New Integration Module: ThorTrading/globalmarkets_hooks.py

Create a dedicated integration module that subscribes to GlobalMarkets signals and orchestrates ThorTrading services.

# ThorTrading/globalmarkets_hooks.py

from django.dispatch import receiver
from GlobalMarkets.signals import market_opened, market_closed
from GlobalMarkets.models import Market

from ThorTrading.services.MarketOpenCapture import capture_market_open
from ThorTrading.services.MarketGrader import start_grading_service, stop_grading_service
from ThorTrading.services.MarketCloseCapture import capture_market_close  # to be factored out
# Later: intraday supervisor, VWAP capturer, 52-week supervisor

CONTROLLED_COUNTRIES = ["USA", "Pre_USA"]  # extend as needed, aligned with constants.CONTROL_COUNTRIES


def _is_controlled_market(market: Market) -> bool:
    return market.country in CONTROLLED_COUNTRIES and market.is_active


@receiver(market_opened)
def handle_market_opened(sender, instance: Market, **kwargs):
    """
    Orchestrate ThorTrading behavior when a market opens.
    """
    if not _is_controlled_market(instance):
        return

    # 1) Capture a market-open snapshot for this market
    capture_market_open(instance)

    # 2) Start grading service (if not already running)
    start_grading_service()

    # TODO: Start intraday supervisor, VWAP capturer, 52-week supervisor, etc.


@receiver(market_closed)
def handle_market_closed(sender, instance: Market, **kwargs):
    """
    Orchestrate ThorTrading behavior when a market closes.
    """
    if not _is_controlled_market(instance):
        return

    country = instance.country

    # 1) Finalize close metrics
    #    (captures market_close + range metrics for the latest session)
    capture_market_close(country, force=False)

    # 2) Stop grading service
    stop_grading_service()

    # TODO: Stop intraday supervisor, VWAP capturer, 52-week supervisor, etc.

Wiring this module

In ThorTrading/apps.py.ready, ensure globalmarkets_hooks is imported so receivers are registered:

def ready(self):
    ...
    # ensure signals are wired
    try:
        import ThorTrading.globalmarkets_hooks  # noqa: F401
    except Exception:
        logger.exception("❌ Failed to import ThorTrading GlobalMarkets hooks")
    ...


This import must happen before GlobalMarkets emits any signals (which it will, once its own ready/monitor starts).

4.3 Factoring Close Capture into a Service: MarketCloseCaptureService

Right now, the close logic lives inside MarketCloseCaptureView.get().

Refactor:

Create a service function in ThorTrading/services/MarketCloseCapture.py:

# ThorTrading/services/MarketCloseCapture.py

from django.db.models import Max
from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.services.quotes import get_enriched_quotes_with_composite
from ThorTrading.services.market_metrics import MarketCloseMetric, MarketRangeMetric

def capture_market_close(country: str, force: bool = False) -> dict:
    """
    Finalize close metrics for the latest session for a given country.
    Returns a dict summarizing status.
    """
    latest_session = (
        MarketSession.objects
        .filter(country=country)
        .aggregate(Max("session_number"))
        .get("session_number__max")
    )
    if latest_session is None:
        return {
            "country": country,
            "status": "no-sessions",
            "message": f"No sessions found for country '{country}'",
        }

    already_closed = MarketSession.objects.filter(
        country=country,
        session_number=latest_session,
        market_close__isnull=False,
    ).exists()

    if already_closed and not force:
        return {
            "country": country,
            "session_number": latest_session,
            "status": "already-closed",
            "message": "Close metrics already populated; use force=True to recompute.",
        }

    enriched, _ = get_enriched_quotes_with_composite()

    close_updated = MarketCloseMetric.update_for_country_on_close(country, enriched)
    range_updated = MarketRangeMetric.update_for_country_on_close(country)

    return {
        "country": country,
        "session_number": latest_session,
        "status": "ok",
        "force": force,
        "close_rows_updated": close_updated,
        "range_rows_updated": range_updated,
    }


Update MarketCloseCaptureView to call this service:

class MarketCloseCaptureView(APIView):
    def get(self, request):
        country = request.GET.get("country")
        force = request.GET.get("force") == "1"
        if not country:
            return Response({"error": "Missing 'country' query parameter"}, status=status.HTTP_400_BAD_REQUEST)

        from ThorTrading.services.MarketCloseCapture import capture_market_close

        result = capture_market_close(country, force=force)

        # Map service result to appropriate HTTP code if desired
        return Response(result, status=status.HTTP_200_OK)


Now GlobalMarkets hooks and user-triggered HTTP calls both reuse the same core logic.

4.4 Grading Loop: Start/Stop via GlobalMarkets

Currently, the MarketGrader is started by the Thor “master stack” and runs forever until stop() is called.

New behavior:

We only start the grading service from GlobalMarkets hooks (handle_market_opened).

We stop grading service from handle_market_closed.

Optionally, add a safety check inside run_grading_loop():

from GlobalMarkets.models import Market

def any_control_markets_open() -> bool:
    return Market.objects.filter(is_control_market=True, is_active=True, status='OPEN').exists()


Then in the loop:

while self.running:
    try:
        if not any_control_markets_open():
            time.sleep(self.check_interval)
            continue

        # existing grading + VWAP minute logic
        ...
    except Exception:
        ...


This ensures that even if the service is mistakenly left running, all real work stops when markets are closed.

4.5 Intraday Supervisor & VWAP Capturer Integration

Note: The exact functions/classes depend on your intraday supervisor files (supervisor.py, intraday_bars.py, session_volume.py, vwap_precompute.py), but the pattern is the same.

Pattern:

Wrap each worker’s loop in a start/stop interface (much like MarketGrader):

# ThorTrading/services/intraday_supervisor.py (example)
class IntradayMarketSupervisor:
    def __init__(...):
        ...

    def start(self):
        # create thread if not already running
        ...

    def stop(self):
        # signal stop_event and join thread
        ...


Expose singletons:

intraday_supervisor = IntradayMarketSupervisor()

def start_intraday_service():
    intraday_supervisor.start()

def stop_intraday_service():
    intraday_supervisor.stop()


In globalmarkets_hooks.py, hook them in:

from ThorTrading.services.intraday_supervisor import start_intraday_service, stop_intraday_service

@receiver(market_opened)
def handle_market_opened(...):
    ...
    start_intraday_service()

@receiver(market_closed)
def handle_market_closed(...):
    ...
    stop_intraday_service()


Same idea for VWAP capturer and 52-week supervisor: give each a start_*_service() / stop_*_service() pair and call those from the hooks.

4.6 Interaction with start_thor_background_stack

Right now, apps.py auto-starts the Thor master stack, which itself spins up all workers.

Goal: reduce duplication and prevent double-starting.

Suggested phases:

Phase 1 (bridge phase)
Keep start_thor_background_stack but:

Remove or disable internal worker start inside that stack for markets that will be controlled by GlobalMarkets.

Let it only initialize shared infrastructure (e.g., logging, Redis connections, config checks).

Phase 2 (clean-up)
Once GlobalMarkets signal-based orchestration is stable:

Simplify start_thor_background_stack to:

Log “ThorTrading ready; workers now orchestrated by GlobalMarkets”

Possibly do nothing else.

Optionally, set THOR_STACK_AUTO_START=0 in web processes and only run the Thor background stack in dedicated worker processes, while still wiring GlobalMarkets hooks in both.

5. Frontend Integration Plan (ThorTrading Only)
5.1 Design: GlobalTimerProvider

We introduce a React context that provides:

tick – increments every second

now – current Date

marketStatus – derived from GlobalMarkets stats endpoint (e.g., OPEN/CLOSED/PREMARKET)

Optional: isUsMarketOpen, isAnyControlMarketOpen, etc.

Pseudo-code sketch:

// src/context/GlobalTimerContext.tsx
import React, { createContext, useContext, useEffect, useState } from "react";
import api from "../api"; // your axios instance

type MarketStatus = {
  isAnyOpen: boolean;
  isUsOpen: boolean;
  // add more fields as needed
};

type GlobalTimerState = {
  tick: number;
  now: Date;
  marketStatus: MarketStatus | null;
};

const GlobalTimerContext = createContext<GlobalTimerState | undefined>(undefined);

export const GlobalTimerProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [tick, setTick] = useState(0);
  const [now, setNow] = useState(() => new Date());
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null);

  useEffect(() => {
    let isMounted = true;

    const intervalId = setInterval(() => {
      if (!isMounted) return;
      setTick((t) => t + 1);
      setNow(new Date());
    }, 1000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, []);

  // Periodically sync with GlobalMarkets stats (e.g. every 10 ticks)
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const resp = await api.get("/global-markets/stats/"); // or your actual endpoint
        // Map API response → MarketStatus
        const status: MarketStatus = {
          isAnyOpen: resp.data.any_open,
          isUsOpen: resp.data.us_open,
        };
        setMarketStatus(status);
      } catch {
        // keep last known status
      }
    };

    if (tick % 10 === 0) {
      fetchStatus();
    }
  }, [tick]);

  const value: GlobalTimerState = { tick, now, marketStatus };
  return <GlobalTimerContext.Provider value={value}>{children}</GlobalTimerContext.Provider>;
};

export const useGlobalTimer = () => {
  const ctx = useContext(GlobalTimerContext);
  if (!ctx) throw new Error("useGlobalTimer must be used within GlobalTimerProvider");
  return ctx;
};


Wrap your app (or at least ThorTrading pages) with <GlobalTimerProvider>.

5.2 ThorTrading Futures Page: Use the Global Timer

Assume a ThorTrading.tsx page that currently does its own setInterval to hit /api/ThorTrading/quotes/latest.

Refactor to:

import { useGlobalTimer } from "../context/GlobalTimerContext";
import api from "../api";

export function ThorTradingPage() {
  const { tick, marketStatus } = useGlobalTimer();
  const [quotes, setQuotes] = useState<any[]>([]);
  const [composite, setComposite] = useState<any | null>(null);

  useEffect(() => {
    const fetchQuotes = async () => {
      try {
        const resp = await api.get("/ThorTrading/quotes/latest");
        setQuotes(resp.data.rows ?? []);
        setComposite(resp.data.total ?? null);
      } catch (e) {
        // handle error/log
      }
    };

    // Example: refresh every 1 second while US is open, every 5 seconds otherwise
    const isUsOpen = marketStatus?.isUsOpen ?? false;
    const interval = isUsOpen ? 1 : 5;

    if (tick % interval === 0) {
      fetchQuotes();
    }
  }, [tick, marketStatus]);

  // render quotes / composite data...
}


Benefits:

No local setInterval inside ThorTrading page.

Same global heartbeat used by:

ThorTrading

GlobalMarkets TSX banner

Any other timed page (Account, Activity, Statements).

5.3 Other Frontend Consumers

You can use the same useGlobalTimer hook in:

Banner time display (top-right clock)

Account summary widgets that need periodic refresh

Market-open session dashboards:

Poll /ThorTrading/market-opens/latest

Poll /ThorTrading/market-opens/stats

All with the same tick & marketStatus, rather than each page inventing its own timer.

6. Migration Plan (Incremental)
Phase 1 – Backend: Signals & Close/Grader Integration

Add ThorTrading/services/MarketCloseCapture.py and refactor MarketCloseCaptureView.

Create ThorTrading/globalmarkets_hooks.py with handlers for market_opened / market_closed:

On open: call capture_market_open(instance) and start_grading_service().

On close: call capture_market_close(country) and stop_grading_service().

Ensure globalmarkets_hooks is imported in ThorTrading/apps.py.ready.

Temporarily keep existing Thor background stack as-is:

But avoid double-starting MarketGrader if hooks will start it (add idempotency checks).

Phase 2 – Backend: Intraday/VWAP/52-Week Orchestration

✅ Status (Dec 2025) — Implemented in `ThorTrading/globalmarkets_hooks.py` + new services.

- Added `ThorTrading/services/vwap_capture.py`, a reusable VWAP minute capture worker with start/stop helpers.
- globalmarkets_hooks now tracks active control markets; first open event starts:
  - MarketOpen capture (per-market)
  - Intraday supervisor worker for that market
  - MarketGrader background thread (singleton)
  - VWAP minute capture + 52-week monitor supervisors (global workers)
- Close events finalize metrics, stop the intraday worker for that market, and only stop global workers (grader, VWAP capture, 52-week supervisor) after the *last* controlled market closes.
- `apps.ThorTradingConfig.ready()` bootstraps already-open markets at process start so workers run even if no new signal fires.
- Legacy `services/stack_start.py` removed; realtime heartbeat now lives in `thor_project/realtime/runtime.py` and runs singly at 1s cadence.

Remaining clean-up: once GlobalMarkets orchestration covers all workers (including MarketOpen capture loop + pre-open/Excel supervisors), simplify `start_thor_background_stack` to only start legacy tasks explicitly requested for non-global deployments.

Phase 3 – Frontend: Global Timer Provider

Implement GlobalTimerProvider / useGlobalTimer and wrap the root app.

Refactor ThorTrading futures page to:

Use tick for polling cadence.

Use marketStatus to adjust frequency (or pause when closed).

Refactor other time-based pages (account, activity/positions, statements) to use useGlobalTimer, removing local setIntervals.

Phase 4 – Cleanup & Hardening

Disable legacy auto-start loops that duplicate GlobalMarkets-controlled behavior.

Add monitoring/logging to ensure:

Workers start when a relevant market opens.

Workers stop when markets close.

Close metrics are populated once per session (except when force=True).

Document the new flow in both ThorTrading.md and GlobalMarkets.md (cross-links).

7. End State (Target)

Once everything in this doc is implemented:

GlobalMarkets:

Owns all market session boundaries and open/close times.

Emits signals that control every ThorTrading worker.

ThorTrading backend:

No longer computes its own notion of “market day” or “session.”

Workers start/stop when GlobalMarkets says so.

Close metrics are automatically finalized on market_closed.

ThorTrading frontend:

Uses a single global heartbeat and market status for all periodic updates.

UI timing is consistent with GlobalMarkets banner and with backend timing.

ThorTrading is thus fully “slaved” to GlobalMarkets, both on the backend (workers) and frontend (timers), while preserving existing APIs and analytics