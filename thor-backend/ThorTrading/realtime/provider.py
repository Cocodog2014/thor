from __future__ import annotations
"""ThorTrading realtime job provider for the heartbeat scheduler.

Single file that registers all ThorTrading jobs. Keeps registration visible and avoids
scattering near-identical wrapper modules.
"""

import logging
from typing import Any, Callable

from core.infra.jobs import Job

logger = logging.getLogger(__name__)


class InlineJob(Job):
    """Minimal Job wrapper with interval-based should_run."""

    def __init__(self, name: str, interval_seconds: float, runner: Callable[[Any], None]):
        self.name = name
        self.interval_seconds = interval_seconds
        self._runner = runner

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:  # noqa: D401
        self._runner(ctx)


def _run_intraday(ctx: Any) -> None:
    from ThorTrading.services.intraday_supervisor.supervisor import intraday_market_supervisor

    intraday_market_supervisor.step_once()


def _run_closed_bars(ctx: Any) -> None:
    from GlobalMarkets.services.active_markets import get_active_control_countries
    from ThorTrading.services.intraday.flush import flush_closed_bars

    countries = get_active_control_countries()
    if not countries:
        return

    for country in countries:
        try:
            total = 0
            batch_size = 500
            while True:
                inserted = flush_closed_bars(country, batch_size=batch_size)
                if not inserted:
                    break
                total += inserted
            if total:
                logger.info("Closed bar flush inserted %s rows for %s", total, country)
        except Exception:
            logger.warning("Closed bar flush failed for %s", country, exc_info=True)


def _run_market_metrics(ctx: Any) -> None:
    from GlobalMarkets.services.active_markets import get_active_control_countries
    from ThorTrading.services.quotes import get_enriched_quotes_with_composite
    from ThorTrading.services.sessions.metrics import MarketHighMetric

    active = set(get_active_control_countries() or [])
    if not active:
        return

    try:
        enriched, _ = get_enriched_quotes_with_composite()
    except Exception:
        logger.exception("market_metrics: failed to load enriched quotes")
        return

    if not enriched:
        return

    # Only operate on quotes whose country is open/controlled right now.
    enriched = [r for r in enriched if r.get("country") in active]
    if not enriched:
        return

    countries = {r["country"] for r in enriched}
    for country in countries:
        try:
            country_rows = [r for r in enriched if r["country"] == country]
            MarketHighMetric.update_from_quotes(country, country_rows)
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
    from GlobalMarkets.services.active_markets import get_active_control_countries
    from ThorTrading.services.quotes import get_enriched_quotes_with_composite
    from ThorTrading.services.indicators.twentyfour import update_24h_for_country

    active = set(get_active_control_countries() or [])
    if not active:
        return

    try:
        enriched, _ = get_enriched_quotes_with_composite()
    except Exception:
        logger.exception("24h: failed to load enriched quotes")
        return

    if not enriched:
        return

    enriched = [r for r in enriched if r.get("country") in active]
    if not enriched:
        return

    countries = {r["country"] for r in enriched}
    for country in countries:
        try:
            country_rows = [r for r in enriched if r["country"] == country]
            update_24h_for_country(country, country_rows)
        except Exception:
            logger.exception("24h: update failed for %s", country)


def _run_preopen(ctx: Any) -> None:
    from GlobalMarkets.services.active_markets import get_control_markets
    from ThorTrading.config.symbols import FUTURES_SYMBOLS
    from ThorTrading.services.analytics.backtest_stats import compute_backtest_stats_for_country_symbol

    markets = get_control_markets()
    if not markets:
        return

    for m in markets:
        try:
            status = m.get_market_status()
            if not status:
                continue

            if status.get("next_event") != "open":
                continue

            seconds = int(status.get("seconds_to_next_event", 0) or 0)
            if seconds <= 0 or seconds > 60:
                continue

            for future in FUTURES_SYMBOLS:
                try:
                    compute_backtest_stats_for_country_symbol(country=m.country, symbol=future)
                except Exception:
                    logger.warning(
                        "preopen_backtest: stats failed for %s/%s", m.country, future, exc_info=True
                    )
        except Exception:
            logger.warning(
                "preopen_backtest: status check failed for market %s", getattr(m, "id", None), exc_info=True
            )


def register(registry):
    jobs = [
        InlineJob("intraday_tick", 1.0, _run_intraday),
        InlineJob("closed_bars_flush", 60.0, _run_closed_bars),
        InlineJob("market_metrics", 10.0, _run_market_metrics),
        InlineJob("market_grader", 1.0, _run_market_grader),
        InlineJob("vwap_minute_capture", 60.0, _run_vwap_minute),
        InlineJob("twentyfour_hour", 30.0, _run_twentyfour),
        InlineJob("preopen_backtest", 30.0, _run_preopen),
    ]

    job_names = []
    for job in jobs:
        try:
            registry.register(job, interval_seconds=job.interval_seconds)
            job_names.append(job.name)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to register job %s", job.name)

    # Week52 is already a Job subclass with its own interval
    try:
        from ThorTrading.services.week52_extremes_job import Week52ExtremesJob

        week52_job = Week52ExtremesJob()
        registry.register(week52_job, interval_seconds=week52_job.interval_seconds)
        job_names.append(week52_job.name)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to register Week52ExtremesJob")

    logger.info("ThorTrading jobs registered: %s", job_names)
    return job_names


__all__ = ["register"]
