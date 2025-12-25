"""24-hour rolling stats update service."""
from __future__ import annotations

import logging
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from ThorTrading.models.Market24h import MarketTrading24Hour
from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.services.intraday_supervisor.utils import safe_decimal

logger = logging.getLogger(__name__)

# Track last seen cumulative volumes per (session_group, symbol) to prevent
# re-adding the same cumulative feed volume on each heartbeat.
_LAST_SEEN_VOLUME: dict[tuple[int, str], int] = {}


@transaction.atomic
def update_24h_for_country(country: str, enriched_rows: Iterable[dict]):
    """Upsert and update rolling 24h stats for each instrument in enriched_rows."""
    if not enriched_rows:
        return {"twentyfour_updates": 0}, {}

    latest_group = (
        MarketSession.objects
        .filter(country=country)
        .exclude(capture_group__isnull=True)
        .order_by('-capture_group')
        .values_list('capture_group', flat=True)
        .first()
    )
    if latest_group is None:
        logger.warning(
            "24h update skipped for %s: no MarketSession capture_group found (quotes=%s)",
            country,
            len(enriched_rows),
        )
        return {"twentyfour_updates": 0}, {}

    now_dt = timezone.now()
    counts = {"twentyfour_updates": 0}
    twentyfour_map = {}

    for row in enriched_rows:
        sym = row.get('instrument', {}).get('symbol') if isinstance(row.get('instrument'), dict) else None
        if not sym:
            continue
        symbol = sym.lstrip('/').upper()

        last = row.get('last')
        high_price = row.get('high_price')
        low_price = row.get('low_price')
        open_price = row.get('open_price')
        prev_close = row.get('previous_close') or row.get('close_price')
        vol = int(row.get('volume') or 0)

        twentyfour, _ = MarketTrading24Hour.objects.get_or_create(
            session_group=latest_group,
            symbol=symbol,
            defaults={
                'session_date': now_dt.date(),
                'country': country,
                'open_price_24h': safe_decimal(open_price),
                'prev_close_24h': safe_decimal(prev_close),
            }
        )
        twentyfour_map[symbol] = twentyfour
        updated = False

        # Initialize extremes
        if twentyfour.low_24h is None and low_price is not None:
            twentyfour.low_24h = safe_decimal(low_price)
            updated = True
        if twentyfour.high_24h is None and high_price is not None:
            twentyfour.high_24h = safe_decimal(high_price)
            updated = True
        # Roll extremes forward
        if high_price is not None:
            hp = safe_decimal(high_price)
            if hp is not None and (twentyfour.high_24h is None or hp > twentyfour.high_24h):
                twentyfour.high_24h = hp
                updated = True
        if low_price is not None:
            lp = safe_decimal(low_price)
            if lp is not None and (twentyfour.low_24h is None or lp < twentyfour.low_24h):
                twentyfour.low_24h = lp
                updated = True

        # Recompute range
        if twentyfour.high_24h is not None and twentyfour.low_24h is not None and twentyfour.open_price_24h not in (None, 0):
            try:
                rng = twentyfour.high_24h - twentyfour.low_24h
                pct = (rng / twentyfour.open_price_24h) * safe_decimal('100')
                twentyfour.range_diff_24h = rng
                twentyfour.range_pct_24h = pct
                updated = True
            except Exception:
                logger.exception("24h range compute failed for %s/%s", country, symbol)

        # Delta volume accumulation to avoid double-counting
        vol_updates = []
        key = (latest_group, symbol)
        prior_seen = _LAST_SEEN_VOLUME.get(key)
        if prior_seen is None:
            prior_seen = int(twentyfour.volume_24h or 0)
        if vol > 0:
            delta = max(vol - prior_seen, 0)
            if delta > 0:
                twentyfour.volume_24h = (twentyfour.volume_24h or 0) + delta
                vol_updates.append('volume_24h')
            _LAST_SEEN_VOLUME[key] = vol

        fields_to_update = []
        if updated:
            fields_to_update.extend(['low_24h', 'high_24h', 'range_diff_24h', 'range_pct_24h'])
        fields_to_update.extend(vol_updates)

        if fields_to_update:
            twentyfour.save(update_fields=fields_to_update)
            counts['twentyfour_updates'] += 1

    return counts, twentyfour_map


__all__ = ["update_24h_for_country"]
