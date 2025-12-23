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
from django.utils.dateparse import parse_datetime
from LiveData.shared.redis_client import live_data_redis
from ThorTrading.config.symbols import FUTURES_SYMBOLS, REDIS_SYMBOL_MAP
from ThorTrading.models.vwap import VwapMinute


def floor_to_minute(dt):
    return dt.replace(second=0, microsecond=0)


def resolve_sample_time(now, quote):
    """Prefer the quote's timestamp when present; fall back to now.

    Expected keys include "timestamp", "ts", or "time" with ISO strings.
    """
    raw = quote.get("timestamp") or quote.get("ts") or quote.get("time")
    if raw:
        try:
            parsed = parse_datetime(str(raw))
            if parsed is not None:
                if timezone.is_naive(parsed):
                    parsed = timezone.make_aware(parsed, timezone.utc)
                return parsed
        except Exception:
            pass
    return now


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
                for sym in FUTURES_SYMBOLS:
                    redis_key = REDIS_SYMBOL_MAP.get(sym, sym)
                    quote = live_data_redis.get_latest_quote(redis_key)
                    if not quote:
                        continue
                    sample_ts = resolve_sample_time(now, quote)
                    current_minute = floor_to_minute(sample_ts)
                    # Skip if already captured this minute for symbol
                    if last_minute_per_symbol.get(sym) == current_minute:
                        continue
                    # Persist row (idempotent per symbol+minute)
                    last_price = _dec(quote.get("last"))
                    cum_vol = _int(quote.get("volume"))
                    obj, created = VwapMinute.objects.get_or_create(
                        symbol=sym,
                        timestamp_minute=current_minute,
                        defaults={
                            "last_price": last_price,
                            "cumulative_volume": cum_vol,
                        },
                    )
                    if created:
                        created_rows += 1
                    else:
                        # Optionally update with fresher data inside same minute
                        update_fields = []
                        if last_price is not None and obj.last_price != last_price:
                            obj.last_price = last_price
                            update_fields.append("last_price")
                        if cum_vol is not None and obj.cumulative_volume != cum_vol:
                            obj.cumulative_volume = cum_vol
                            update_fields.append("cumulative_volume")
                        if update_fields:
                            obj.save(update_fields=update_fields)
                    last_minute_per_symbol[sym] = current_minute
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

