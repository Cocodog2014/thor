from datetime import datetime, timezone as dt_timezone

from django.utils import timezone, dateparse

from ThorTrading.models.MarketIntraDay import MarketIntraday
from ThorTrading.services.country_codes import normalize_country_code
from .utils import safe_decimal


UTC = dt_timezone.utc


def _resolve_minute_bucket(timestamp_value, fallback_now):
    """Return UTC minute bucket for the provided timestamp (or fallback)."""
    dt = None

    if isinstance(timestamp_value, (int, float)):
        dt = datetime.fromtimestamp(timestamp_value, tz=UTC)
    elif isinstance(timestamp_value, str):
        ts = timestamp_value.strip()
        dt = dateparse.parse_datetime(ts)
        if dt is None:
            try:
                dt = datetime.fromtimestamp(float(ts), tz=UTC)
            except (ValueError, TypeError):
                dt = None
    elif isinstance(timestamp_value, datetime):
        dt = timestamp_value

    if dt is None:
        dt = fallback_now

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, UTC)

    return dt.astimezone(UTC).replace(second=0, microsecond=0)


def update_intraday_bars_for_country(country: str, enriched_rows, twentyfour_map):
    """Create/get 1-minute OHLCV bar per instrument.

    Expects twentyfour_map from feed_24h so we can link the bar.
    Returns counts dict: {'intraday_bars': int}
    """
    if not enriched_rows:
        return {'intraday_bars': 0}

    now_dt = timezone.now()
    counts = {'intraday_bars': 0, 'intraday_updates': 0}

    for row in enriched_rows:
        sym = row.get('instrument', {}).get('symbol')
        if not sym:
            continue
        future = sym.lstrip('/').upper()
        last = row.get('last')
        last_price = safe_decimal(last)
        if last_price is None:
            continue
        vol = int(row.get('volume') or 0)
        timestamp_value = row.get('timestamp')
        minute_bucket = _resolve_minute_bucket(timestamp_value, now_dt)
        twentyfour = twentyfour_map.get(future)
        if twentyfour is None:
            # 24h row not created; skip
            continue

        obj, created = MarketIntraday.objects.get_or_create(
            timestamp_minute=minute_bucket,
            country=country,
            future=future,
            defaults={
                'twentyfour': twentyfour,
                'open_1m': last_price,
                'high_1m': last_price,
                'low_1m': last_price,
                'close_1m': last_price,
                'volume_1m': vol,
                'bid_last': safe_decimal(row.get('bid')),
                'ask_last': safe_decimal(row.get('ask')),
                'spread_last': safe_decimal(row.get('spread')),
            }
        )
        if created:
            counts['intraday_bars'] += 1
            continue

        updated_fields = []

        if obj.high_1m is None or last_price > obj.high_1m:
            obj.high_1m = last_price
            updated_fields.append('high_1m')
        if obj.low_1m is None or last_price < obj.low_1m:
            obj.low_1m = last_price
            updated_fields.append('low_1m')

        obj.close_1m = last_price
        updated_fields.append('close_1m')

        if vol is not None and vol >= 0 and vol != obj.volume_1m:
            obj.volume_1m = vol
            updated_fields.append('volume_1m')

        bid = safe_decimal(row.get('bid'))
        if bid is not None and bid != obj.bid_last:
            obj.bid_last = bid
            updated_fields.append('bid_last')

        ask = safe_decimal(row.get('ask'))
        if ask is not None and ask != obj.ask_last:
            obj.ask_last = ask
            updated_fields.append('ask_last')

        if bid is not None and ask is not None:
            spread = ask - bid
            if obj.spread_last != spread:
                obj.spread_last = spread
                updated_fields.append('spread_last')

        if updated_fields:
            obj.save(update_fields=updated_fields)
            counts['intraday_updates'] += 1

    return counts

