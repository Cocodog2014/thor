from django.utils import timezone
from FutureTrading.models.MarketIntraDay import MarketIntraday
from .utils import safe_decimal


def update_intraday_bars_for_country(country: str, enriched_rows, twentyfour_map):
    """Create/get 1-minute OHLCV bar per instrument.

    Expects twentyfour_map from feed_24h so we can link the bar.
    Returns counts dict: {'intraday_bars': int}
    """
    if not enriched_rows:
        return {'intraday_bars': 0}

    now_dt = timezone.now()
    minute_bucket = now_dt.replace(second=0, microsecond=0)
    counts = {'intraday_bars': 0}

    for row in enriched_rows:
        sym = row.get('instrument', {}).get('symbol')
        if not sym:
            continue
        future = sym.lstrip('/').upper()
        last = row.get('last')
        vol = int(row.get('volume') or 0)
        twentyfour = twentyfour_map.get(future)
        if twentyfour is None:
            # 24h row not created; skip
            continue

        obj, created = MarketIntraday.objects.get_or_create(
            timestamp_minute=minute_bucket,
            country=country,
            future=future,
            defaults={
                'market_code': country,
                'twentyfour': twentyfour,
                'open_1m': safe_decimal(last),
                'high_1m': safe_decimal(last),
                'low_1m': safe_decimal(last),
                'close_1m': safe_decimal(last),
                'volume_1m': vol,
            }
        )
        if created:
            counts['intraday_bars'] += 1

    return counts
