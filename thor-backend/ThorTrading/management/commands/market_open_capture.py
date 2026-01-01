import logging
from django.core.management.base import BaseCommand
from GlobalMarkets.models.market import Market
from GlobalMarkets.services.market_clock import is_market_open_now
from ThorTrading.studies.futures_total.services.session_capture import (
    capture_open_for_market,
    _market_local_date,
)
from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.studies.futures_total.services.global_market_gate import (
    open_capture_allowed,
    session_tracking_allowed,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run market open capture once for active markets (optionally filtered by country)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            dest="country",
            help="Only capture the specified country (case-insensitive match on Market.country)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            help="Force capture even if an OPEN capture already exists for the market-local date",
        )

    def handle(self, *args, **options):
        country_filter = (options.get("country") or "").strip()
        force_capture = bool(options.get("force"))

        qs = Market.objects.filter(is_active=True)
        if country_filter:
            qs = qs.filter(country__iexact=country_filter)

        markets = list(qs)
        if not markets:
            msg = "No active markets found"
            if country_filter:
                msg += f" matching country={country_filter!r}"
            self.stdout.write(self.style.WARNING(msg))
            return

        def _has_capture_for_date(market, market_date):
            """Check if an OPEN capture exists for the market-local date."""
            country = getattr(market, "country", None)
            return MarketSession.objects.filter(
                country=country,
                capture_kind="OPEN",
                year=market_date.year,
                month=market_date.month,
                date=market_date.day,
            ).exists()

        for market in markets:
            country = getattr(market, "country", "?")
            if not session_tracking_allowed(market):
                self.stdout.write(f"⏭️  {country}: session tracking disabled; skipping")
                continue
            if not open_capture_allowed(market):
                self.stdout.write(f"⏭️  {country}: open capture disabled; skipping")
                continue
            if not is_market_open_now(market):
                self.stdout.write(f"🔒 {country}: market not open right now; skipping")
                continue

            market_date = _market_local_date(market)
            already = False
            try:
                already = _has_capture_for_date(market, market_date)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed checking capture history for %s: %s", country, exc)

            if already and not force_capture:
                self.stdout.write(f"✅ {country}: already has OPEN capture for {market_date}; skip (use --force to override)")
                continue

            self.stdout.write(f"🌅 {country}: running market open capture for {market_date}")
            try:
				capture_open_for_market(market)
            except Exception:
                logger.exception("Market open capture failed for %s", country)
                self.stdout.write(self.style.ERROR(f"❌ {country}: capture failed (see logs)"))
            else:
                self.stdout.write(self.style.SUCCESS(f"✅ {country}: capture completed"))
