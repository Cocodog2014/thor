"""Capture VWAP minute snapshots.

Reads latest quotes from Redis and stores one row per symbol per minute
in `VwapMinute`. No VWAP math performed here; this is a raw data feed
for downstream VWAP calculations.

Usage:
    python manage.py capture_vwap_minutes            # default 60s interval
    python manage.py capture_vwap_minutes --interval 10

Interval < 60s simply increases sampling granularity; persistence only
occurs when the minute changes.
"""
from __future__ import annotations

import time
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from LiveData.shared.redis_client import live_data_redis
from ThorTrading.constants import FUTURES_SYMBOLS, REDIS_SYMBOL_MAP
from ThorTrading.models.vwap import VwapMinute


def floor_to_minute(dt):
    return dt.replace(second=0, microsecond=0)


class Command(BaseCommand):
    help = "Capture per-minute VWAP source rows (raw Redis snapshots)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=60,
            help="Sampling interval seconds (default: 60). Persistence still minute-based."\
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        self.stdout.write(self.style.SUCCESS(f"Starting VWAP minute capture (interval={interval}s)"))
        self.stdout.write(self.style.WARNING("Press Ctrl+C to stop"))

        # Track last persisted minute per symbol to avoid duplicate rows when interval < 60
        last_minute_per_symbol = {}
        sample_count = 0
        created_rows = 0
        try:
            while True:
                sample_count += 1
                now = timezone.now()
                current_minute = floor_to_minute(now)
                for sym in FUTURES_SYMBOLS:
                    redis_key = REDIS_SYMBOL_MAP.get(sym, sym)
                    quote = live_data_redis.get_latest_quote(redis_key)
                    if not quote:
                        continue
                    # Skip if already captured this minute for symbol
                    if last_minute_per_symbol.get(sym) == current_minute:
                        continue
                    # Persist row
                    # Model no longer has bid_price / ask_price fields (removed in migration 0061).
                    # Persist only the fields that exist: last_price, cumulative_volume.
                    row = VwapMinute.objects.create(
                        symbol=sym,
                        timestamp_minute=current_minute,
                        last_price=_dec(quote.get("last")),
                        cumulative_volume=_int(quote.get("volume")),
                    )
                    last_minute_per_symbol[sym] = current_minute
                    created_rows += 1
                if sample_count % 10 == 0:  # periodic progress
                    self.stdout.write(f"Samples={sample_count} rows_created={created_rows}")
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS(
                f"Stopped. Samples={sample_count} rows_created={created_rows}"
            ))


def _dec(val):
    if val in (None, "", " "):
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


def _int(val):
    if val in (None, "", " "):
        return None
    try:
        return int(val)
    except Exception:
        try:
            return int(float(val))
        except Exception:
            return None

