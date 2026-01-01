from __future__ import annotations

import logging

from GlobalMarkets.models.market import Market
from GlobalMarkets.services.market_clock import is_market_open_now
from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.studies.futures_total.services.global_market_gate import (
    open_capture_allowed,
    session_tracking_allowed,
)
from ThorTrading.studies.futures_total.services.session_capture import (
    _market_local_date,
    capture_open_for_market,
)

logger = logging.getLogger(__name__)


def run(*, country: str | None, force: bool, stdout, style) -> None:
    country_filter = (country or "").strip()
    force_capture = bool(force)

    qs = Market.objects.filter(is_active=True)
    if country_filter:
        qs = qs.filter(country__iexact=country_filter)

    markets = list(qs)
    if not markets:
        msg = "No active markets found"
        if country_filter:
            msg += f" matching country={country_filter!r}"
        stdout.write(style.WARNING(msg))
        return

    def _has_capture_for_date(market, market_date):
        country_val = getattr(market, "country", None)
        return MarketSession.objects.filter(
            country=country_val,
            capture_kind="OPEN",
            year=market_date.year,
            month=market_date.month,
            date=market_date.day,
        ).exists()

    for market in markets:
        country_val = getattr(market, "country", "?")
        if not session_tracking_allowed(market):
            stdout.write(f"⏭️  {country_val}: session tracking disabled; skipping")
            continue
        if not open_capture_allowed(market):
            stdout.write(f"⏭️  {country_val}: open capture disabled; skipping")
            continue
        if not is_market_open_now(market):
            stdout.write(f"🔒 {country_val}: market not open right now; skipping")
            continue

        market_date = _market_local_date(market)
        already = False
        try:
            already = _has_capture_for_date(market, market_date)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed checking capture history for %s: %s", country_val, exc)

        if already and not force_capture:
            stdout.write(
                f"✅ {country_val}: already has OPEN capture for {market_date}; skip (use --force to override)"
            )
            continue

        stdout.write(f"🌅 {country_val}: running market open capture for {market_date}")
        try:
            capture_open_for_market(market)
        except Exception:
            logger.exception("Market open capture failed for %s", country_val)
            stdout.write(style.ERROR(f"❌ {country_val}: capture failed (see logs)"))
        else:
            stdout.write(style.SUCCESS(f"✅ {country_val}: capture completed"))
