from __future__ import annotations

import logging
from typing import Dict, Iterable

from django.db import transaction

from ThorTrading.models.MarketSession import MarketSession

logger = logging.getLogger(__name__)

# Cache last seen cumulative volume per (capture_group, symbol) to prevent
# re-adding the same cumulative feed volume on each tick.
_LAST_SEEN: Dict[tuple[int, str], int] = {}


@transaction.atomic
def update_session_volume_for_country(country: str, enriched_rows: Iterable[dict]):
    """Delta-accumulate session_volume from cumulative quote volumes.

    Mirrors the VWAP delta approach: uses cumulative feed volume and stores
    only the positive delta since the last seen cumulative for a given
    capture_group + symbol pair.
    """
    # Fast exit when no quotes
    enriched_rows = list(enriched_rows or [])
    if not enriched_rows:
        return {"session_volume_updates": 0}

    latest_group = (
        MarketSession.objects
        .filter(country=country)
        .exclude(capture_group__isnull=True)
        .order_by('-capture_group')
        .values_list('capture_group', flat=True)
        .first()
    )
    if latest_group is None:
        return {"session_volume_updates": 0}

    # Build a cache of sessions for this capture_group keyed by symbol.
    sessions = {
        row.symbol: row
        for row in MarketSession.objects.filter(country=country, capture_group=latest_group)
    }

    updates = 0
    for row in enriched_rows:
        sym = (row.get('instrument', {}) or {}).get('symbol') or ''
        symbol = sym.lstrip('/').upper()
        if not symbol or symbol == 'TOTAL':
            continue

        vol = row.get('volume')
        try:
            vol_int = int(vol)
        except Exception:
            continue
        if vol_int <= 0:
            continue

        session = sessions.get(symbol)
        if not session:
            continue

        key = (latest_group, symbol)
        prior_seen = _LAST_SEEN.get(key)
        if prior_seen is None:
            prior_seen = int(session.session_volume or 0)

        delta = vol_int - prior_seen
        if delta <= 0:
            _LAST_SEEN[key] = vol_int
            continue

        session.session_volume = (session.session_volume or 0) + delta
        session.save(update_fields=["session_volume"])
        _LAST_SEEN[key] = vol_int
        updates += 1

    if updates and logger.isEnabledFor(logging.DEBUG):
        logger.debug("Session volume updated: country=%s capture_group=%s rows=%s", country, latest_group, updates)

    return {"session_volume_updates": updates}

