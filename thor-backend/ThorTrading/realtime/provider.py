from __future__ import annotations
"""
ThorTrading realtime job provider for the heartbeat scheduler.

Single file that registers all ThorTrading jobs.
"""

import logging
from typing import Any, Callable, Iterable

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


def _flush_closed_bars_for_countries(
    countries: Iterable[str],
    *,
    label: str,
    batch_size: int = 500,
    max_loops_per_country: int = 50,
) -> None:
    """Drain Redis closed-bar queues into DB for each country."""
    from ThorTrading.services.intraday.flush import flush_closed_bars

    for country in countries:
        try:
            total = 0
            loops = 0
            while loops < max_loops_per_country:
                inserted = flush_closed_bars(country, batch_size=batch_size)
                if not inserted:
                    break
                total += inserted
                loops += 1

            if total:
                logger.info("%s inserted %s rows for %s", label, total, country)
        except Exception:
            logger.warning("%s failed for %s", label, country, exc_info=True)


# -------------------------------------------------------------------
# Job runners
# -------------------------------------------------------------------
def _run_intraday_tick(ctx: Any) -> None:
    """1-second tick: build ticks + current 1m bars in Redis."""
    from ThorTrading.services.intraday_supervisor.supervisor import intraday_market_supervisor

    intraday_market_supervisor.step_once()


def _run_intraday_flush(ctx: Any) -> None:
    """Fast flush for newly closed 1m bars."""
    countries = _active_countries()
    if not countries:
        return

    _flush_closed_bars_for_countries(
        countries,
        label="intraday_flush",
        batch_size=500,
        max_loops_per_country=20,
    )


def _run_closed_bars_flush(ctx: Any) -> None:
    """Slow safety flush to drain any backlog."""
    countries = _active_countries()
    if not countries:
        return

    _flush_closed_bars_for_countries(
        countries,
        label="closed_bars_flush",
        batch_size=500,
        max_loops_per_country=100,
    )


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

    for country in {r["country"] for r in enriched if r.get("country")}:
        try:
            MarketHighMetric.update_from_quotes(
                country,
                [r for r in enriched if r["country"] == country],
            )
        except Exception:
            logger.exception("market_metrics: update failed for %s", country)


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

    for country in {r["country"] for r in enriched if r.get("country")}:
        try:
            update_24h_for_country(
                country,
                [r for r in enriched if r["country"] == country],
            )
        except Exception:
            logger.exception("twentyfour_hour: update failed for %s", country)


# -------------------------------------------------------------------
# Registration
# -------------------------------------------------------------------
def register(registry):
    jobs = [
        InlineJob("intraday_tick", 1.0, _run_intraday_tick),
        InlineJob("intraday_flush", 5.0, _run_intraday_flush),
        InlineJob("closed_bars_flush", 60.0, _run_closed_bars_flush),
        InlineJob("market_metrics", 10.0, _run_market_metrics),
        InlineJob("market_grader", 1.0, _run_market_grader),
        InlineJob("vwap_minute_capture", 60.0, _run_vwap_minute),
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
