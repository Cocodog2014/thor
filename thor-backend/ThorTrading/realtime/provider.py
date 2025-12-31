from __future__ import annotations
"""
ThorTrading realtime job provider for the heartbeat scheduler.

This provider registers ThorTrading jobs only.

Key rule:
- GlobalMarkets is the source of truth for OPEN markets + active routing (session:<n>).
- ThorTrading consumes that routing snapshot for streaming/flush.
- ThorTrading is responsible for creating/updating ThorTrading DB artifacts (MarketSession, intraday bars, stats)
  based on that OPEN state (including restart-safe open capture scans).
"""

import logging
from typing import Any, Callable

from core.infra.jobs import Job

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Minimal inline Job wrapper
# -------------------------------------------------------------------
class InlineJob(Job):
    """Minimal Job wrapper with interval-based should_run."""

    def __init__(self, name: str, interval_seconds: float, runner: Callable[[Any], None]):
        self.name = name
        self.interval_seconds = float(interval_seconds)
        self._runner = runner

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        self._runner(ctx)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def _active_countries() -> list[str]:
    """Countries currently controlled/open for realtime work."""
    from ThorTrading.config.markets import get_control_countries

    return list(get_control_countries(require_session_capture=True) or [])


# -------------------------------------------------------------------
# Job runners
# -------------------------------------------------------------------
def _run_intraday_tick(ctx: Any) -> None:
    """1-second tick: build ticks + current 1m bars in Redis."""
    from ThorTrading.intraday.supervisor import IntradayCollectorSupervisor

    IntradayCollectorSupervisor().tick()


def _run_intraday_flush(ctx: Any) -> None:
    """Fast flush for newly closed 1m bars."""
    from LiveData.shared.redis_client import live_data_redis
    from ThorTrading.intraday.flush import flush_closed_bars

    routing_key = live_data_redis.get_active_session_key(asset_type="futures")
    if not routing_key:
        logger.debug("intraday_flush skipped: no active session routing key")
        return

    try:
        total = 0
        loops = 0
        while loops < 20:
            inserted = flush_closed_bars(routing_key, batch_size=500)
            if not inserted:
                break
            total += inserted
            loops += 1
        if total:
            logger.info("intraday_flush inserted %s rows for %s", total, routing_key)
    except Exception:
        logger.warning("intraday_flush failed for %s", routing_key, exc_info=True)


def _run_open_capture_scan(ctx: Any) -> None:
    """State-based open capture.

    Ensures we create MarketSession rows even if the app restarts while a market is already OPEN.
    """
    from ThorTrading.GlobalMarketGate.open_capture import check_for_market_opens_and_capture

    try:
        check_for_market_opens_and_capture()
    except Exception:
        logger.exception("open_capture_scan failed")


def _run_closed_bars_flush(ctx: Any) -> None:
    """Deeper flush pass to drain Redis closed bars queue."""
    from LiveData.shared.redis_client import live_data_redis
    from ThorTrading.intraday.flush import flush_closed_bars

    routing_key = live_data_redis.get_active_session_key(asset_type="futures")
    if not routing_key:
        logger.debug("closed_bars_flush skipped: no active session routing key")
        return

    try:
        total = 0
        loops = 0
        while loops < 100:
            inserted = flush_closed_bars(routing_key, batch_size=500)
            if not inserted:
                break
            total += inserted
            loops += 1
        if total:
            logger.info("closed_bars_flush inserted %s rows for %s", total, routing_key)
    except Exception:
        logger.warning("closed_bars_flush failed for %s", routing_key, exc_info=True)


def _run_market_metrics(ctx: Any) -> None:
    from ThorTrading.services.quotes import get_enriched_quotes_with_composite
    from ThorTrading.services.sessions.metrics import MarketHighMetric

    active = set(_active_countries())
    if not active:
        return

    try:
        enriched, _ = get_enriched_quotes_with_composite()
    except Exception:
        logger.exception("market_metrics: failed to load enriched quotes")
        return

    if not enriched:
        return

    enriched = [r for r in enriched if r.get("country") in active]
    if not enriched:
        return

    for country in sorted(active):
        country_rows = [r for r in enriched if r.get("country") == country]
        if country_rows:
            MarketHighMetric.update_from_quotes(country, country_rows)


def _run_market_grader(ctx: Any) -> None:
    from ThorTrading.services.sessions.grading import grade_pending_once

    try:
        grade_pending_once()
    except Exception:
        logger.exception("market_grader: grading pass failed")


def _run_vwap_minute(ctx: Any) -> None:
    from ThorTrading.services.indicators.vwap_minute import capture_vwap_minute

    samples, rows_created = capture_vwap_minute(ctx.shared_state)
    if samples or rows_created:
        logger.debug("VWAP capture: samples=%s rows=%s", samples, rows_created)


def _run_twentyfour(ctx: Any) -> None:
    from ThorTrading.services.quotes import get_enriched_quotes_with_composite
    from ThorTrading.services.indicators.twentyfour import update_24h_for_country

    active = set(_active_countries())
    if not active:
        return

    try:
        enriched, _ = get_enriched_quotes_with_composite()
    except Exception:
        logger.exception("twentyfour_hour: failed to load enriched quotes")
        return

    if not enriched:
        return

    enriched = [r for r in enriched if r.get("country") in active]
    if not enriched:
        return

    for country in sorted(active):
        update_24h_for_country(country, enriched)


# -------------------------------------------------------------------
# Provider entrypoint
# -------------------------------------------------------------------
def register(registry: Any) -> list[str]:
    jobs = [
        InlineJob("intraday_tick", 1.0, _run_intraday_tick),
        InlineJob("intraday_flush", 2.0, _run_intraday_flush),
        InlineJob("closed_bars_flush", 10.0, _run_closed_bars_flush),

        # ✅ Restart-safe: create MarketSession rows while market is OPEN
        InlineJob("gm.open_capture_scan", 5.0, _run_open_capture_scan),

        InlineJob("market_metrics", 10.0, _run_market_metrics),
        InlineJob("market_grader", 15.0, _run_market_grader),
        InlineJob("vwap_minute", 60.0, _run_vwap_minute),
        InlineJob("twentyfour_hour", 30.0, _run_twentyfour),
    ]

    job_names: list[str] = []

    for job in jobs:
        try:
            registry.register(job, interval_seconds=job.interval_seconds)
            job_names.append(job.name)
        except Exception:
            logger.exception("Failed to register job %s", job.name)

    # Week52 job (already a Job subclass)
    try:
        from ThorTrading.services.week52_extremes_job import Week52ExtremesJob

        week52_job = Week52ExtremesJob()
        registry.register(week52_job, interval_seconds=week52_job.interval_seconds)
        job_names.append(week52_job.name)
    except Exception:
        logger.exception("Failed to register Week52ExtremesJob")

    logger.info("ThorTrading jobs registered: %s", job_names)
    return job_names


__all__ = ["register"]

