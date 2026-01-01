from __future__ import annotations

import time
from decimal import Decimal

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from LiveData.shared.redis_client import live_data_redis
from ThorTrading.models import TradingInstrument
from ThorTrading.models.vwap import VwapMinute


def floor_to_minute(dt):
    return dt.replace(second=0, microsecond=0)


def resolve_sample_time(now, quote):
    """Prefer the quote's timestamp when present; fall back to now."""
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


def _tracked_symbols(*, stdout, style):
    try:
        qs = TradingInstrument.objects.filter(is_active=True, is_watchlist=True)
        symbols = []
        for sym in qs.values_list("symbol", flat=True):
            if not sym:
                continue
            symbols.append((sym.lstrip("/").upper(), sym))
        return symbols
    except Exception:
        stdout.write(style.ERROR("Failed to load tracked instruments"))
        return []


def run(*, interval: int, stdout, style) -> None:
    stdout.write(style.SUCCESS(f"Starting VWAP minute capture (interval={interval}s)"))
    stdout.write(style.WARNING("Press Ctrl+C to stop"))

    last_minute_per_symbol = {}
    sample_count = 0
    created_rows = 0

    try:
        while True:
            sample_count += 1
            now = timezone.now()

            for norm_sym, redis_key in _tracked_symbols(stdout=stdout, style=style):
                quote = live_data_redis.get_latest_quote(redis_key)
                if not quote:
                    continue
                sample_ts = resolve_sample_time(now, quote)
                current_minute = floor_to_minute(sample_ts)
                if last_minute_per_symbol.get(norm_sym) == current_minute:
                    continue

                last_price = _dec(quote.get("last"))
                cum_vol = _int(quote.get("volume"))
                obj, created = VwapMinute.objects.get_or_create(
                    symbol=norm_sym,
                    timestamp_minute=current_minute,
                    defaults={
                        "last_price": last_price,
                        "cumulative_volume": cum_vol,
                    },
                )
                if created:
                    created_rows += 1
                else:
                    update_fields = []
                    if last_price is not None and obj.last_price != last_price:
                        obj.last_price = last_price
                        update_fields.append("last_price")
                    if cum_vol is not None and obj.cumulative_volume != cum_vol:
                        obj.cumulative_volume = cum_vol
                        update_fields.append("cumulative_volume")
                    if update_fields:
                        obj.save(update_fields=update_fields)

                last_minute_per_symbol[norm_sym] = current_minute

            if sample_count % 10 == 0:
                stdout.write(f"Samples={sample_count} rows_created={created_rows}")
            time.sleep(interval)
    except KeyboardInterrupt:
        stdout.write(style.SUCCESS(f"Stopped. Samples={sample_count} rows_created={created_rows}"))
