from __future__ import annotations
from django.core.management.base import BaseCommand

from ThorTrading.services.config.country_codes import normalize_country_code
from ThorTrading.models.MarketIntraDay import MarketIntraday
from ThorTrading.models.Martket24h import MarketTrading24Hour
from GlobalMarkets.models.market import Market

# Canonical set aligned with GlobalMarkets.ALLOWED_CONTROL_COUNTRIES
CANONICAL = {
    "Japan",
    "China",
    "India",
    "Germany",
    "United Kingdom",
    "Pre_USA",
    "USA",
    "Canada",
    "Mexico",
    "Futures",
}

# Legacy bad labels we have seen
CLEANUP = {
    "Shanghai": "China",
    "SSE": "China",
    "Great Britain": "United Kingdom",
    "England": "United Kingdom",
}


def _normalize(value: str | None) -> str | None:
    if not value:
        return value
    raw = value.strip()
    if not raw:
        return raw
    if raw in CLEANUP:
        raw = CLEANUP[raw]
    normalized = normalize_country_code(raw)
    if normalized in CLEANUP:
        normalized = CLEANUP[normalized]
    return normalized


class Command(BaseCommand):
    help = "Normalize country fields for intraday and market rows to canonical values."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report changes without writing them.",
        )
        parser.add_argument("--verbose", action="store_true", help="Log counts as they accrue.")

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        verbose = options.get("verbose", False)

        def maybe_save(obj, fields):
            if dry_run:
                return 0
            obj.save(update_fields=fields)
            return 1

        updated = {
            "markets": 0,
            "intraday": 0,
            "intraday_deleted": 0,
            "market24h": 0,
        }

        # Normalize Market.country
        for m in Market.objects.all():
            before = m.country
            after = _normalize(before)
            if not after or after not in CANONICAL:
                continue
            if after != before:
                m.country = after
                updated["markets"] += maybe_save(m, ["country"])

        # Normalize MarketIntraday.country
        # Use deterministic ordering so deletes/updates are stable
        for row in MarketIntraday.objects.order_by(
            "timestamp_minute", "symbol", "country", "id"
        ).iterator():
            before_country = row.country
            after_country = _normalize(before_country)
            if not after_country or after_country not in CANONICAL:
                continue

            updated_fields = []

            if after_country != before_country:
                # If a row with the desired canonical key already exists, drop this one
                conflict = (
                    MarketIntraday.objects.filter(
                        timestamp_minute=row.timestamp_minute,
                        symbol=row.symbol,
                        country=after_country,
                    )
                    .exclude(pk=row.pk)
                    .first()
                )
                if conflict:
                    updated["intraday_deleted"] += 1
                    if not dry_run:
                        row.delete()
                    continue

                row.country = after_country
                updated_fields.append("country")

            if updated_fields:
                updated["intraday"] += maybe_save(row, updated_fields)

        # Normalize MarketTrading24Hour.country
        for row in MarketTrading24Hour.objects.all():
            before = row.country
            after = _normalize(before)
            if not after or after not in CANONICAL:
                continue
            if after != before:
                row.country = after
                updated["market24h"] += maybe_save(row, ["country"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Normalization complete (dry_run={dry_run}). "
                f"Markets={updated['markets']} Intraday={updated['intraday']} "
                f"IntradayDeleted={updated['intraday_deleted']} "
                f"Market24h={updated['market24h']}"
            )
        )

        if dry_run:
            self.stdout.write("No changes written (dry-run).")
        if verbose:
            self.stdout.write(
                f"Updated: markets={updated['markets']} intraday={updated['intraday']} "
                f"deleted={updated['intraday_deleted']} market24h={updated['market24h']}"
            )
