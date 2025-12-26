from __future__ import annotations

import logging
from typing import Iterable

from django.db import transaction

from LiveData.shared.redis_client import live_data_redis
from ThorTrading.models.MarketSession import MarketSession

logger = logging.getLogger(__name__)

LAST_SEEN_TTL_SECONDS = 60 * 60 * 24 * 3  # keep a few days to survive restarts


def _last_seen_key(country: str, session_group: int, symbol: str) -> str:
    # Scoped to session_volume to avoid collisions with 24h tracking.
    return f"thor:last_seen_vol_session:{(country or '').lower()}:{session_group}:{symbol}"


def _get_last_seen(country: str, session_group: int, symbol: str) -> int | None:
    try:
        raw = live_data_redis.client.get(_last_seen_key(country, session_group, symbol))
        if raw is None:
            return None
        return int(raw)
    except Exception:
        logger.debug("session_volume last_seen redis get failed for %s/%s", country, symbol, exc_info=True)
        return None


def _set_last_seen(country: str, session_group: int, symbol: str, vol: int) -> None:
    try:
        live_data_redis.client.set(_last_seen_key(country, session_group, symbol), int(vol), ex=LAST_SEEN_TTL_SECONDS)
    except Exception:
        logger.debug("session_volume last_seen redis set failed for %s/%s", country, symbol, exc_info=True)


@transaction.atomic
def update_session_volume_for_country(country: str, enriched_rows: Iterable[dict]):
    """Delta-accumulate session_volume from cumulative quote volumes.

    Mirrors the VWAP delta approach: uses cumulative feed volume and stores
    only the positive delta since the last seen cumulative for a given
    session_group + symbol pair.
    """
    # Fast exit when no quotes
    enriched_rows = list(enriched_rows or [])
    if not enriched_rows:
        return {"session_volume_updates": 0}

    session_group = (
        MarketSession.objects
        .filter(country=country)
        .exclude(capture_group__isnull=True)
        .order_by('-capture_group')
        .values_list('capture_group', flat=True)
        .first()
    )
    if session_group is None:
        return {"session_volume_updates": 0}

    # Build a cache of sessions for this session_group keyed by symbol.
    sessions = {
        row.symbol: row
        for row in MarketSession.objects.filter(country=country, capture_group=session_group)
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

        key = (session_group, symbol)
        prior_seen = _get_last_seen(country, session_group, symbol)
        if prior_seen is None:
            prior_seen = int(session.session_volume or 0)

        delta = vol_int - prior_seen
        if delta <= 0:
            _set_last_seen(country, session_group, symbol, vol_int)
            continue

        session.session_volume = (session.session_volume or 0) + delta
        session.save(update_fields=["session_volume"])
        _set_last_seen(country, session_group, symbol, vol_int)
        updates += 1

    if updates and logger.isEnabledFor(logging.DEBUG):
        logger.debug("Session volume updated: country=%s session_group=%s rows=%s", country, session_group, updates)

    return {"session_volume_updates": updates}

