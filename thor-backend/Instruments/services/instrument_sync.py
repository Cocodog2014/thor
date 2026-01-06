from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model

from Instruments.models import Instrument, UserInstrumentWatchlistItem
from LiveData.schwab.signal_control import suppress_schwab_subscription_signals


def get_owner_user_id() -> int:
    return int(getattr(settings, "THOR_OWNER_USER_ID", 1) or 1)


def ensure_owner_watchlist_for_instrument(instrument: Instrument) -> None:
    """Keep owner (user 1) watchlist aligned to Instruments catalog.

    - If instrument is active: ensure a watchlist row exists (enabled+stream).
    - If instrument is inactive: remove it from owner watchlist.

    This is intentionally simple: Instruments is the single symbol CRUD surface.
    """

    owner_user_id = get_owner_user_id()

    if not instrument.is_active:
        with suppress_schwab_subscription_signals():
            UserInstrumentWatchlistItem.objects.filter(user_id=owner_user_id, instrument=instrument).delete()
        return

    defaults = {"enabled": True, "stream": True}

    # Append to end when first added.
    existing = UserInstrumentWatchlistItem.objects.filter(user_id=owner_user_id, instrument=instrument).first()
    if existing:
        if existing.enabled != defaults["enabled"] or existing.stream != defaults["stream"]:
            with suppress_schwab_subscription_signals():
                UserInstrumentWatchlistItem.objects.filter(id=existing.id).update(**defaults)
        return

    max_order = (
        UserInstrumentWatchlistItem.objects.filter(user_id=owner_user_id)
        .order_by("-order")
        .values_list("order", flat=True)
        .first()
    )
    next_order = int(max_order or 0) + 1

    with suppress_schwab_subscription_signals():
        UserInstrumentWatchlistItem.objects.create(
            user_id=owner_user_id,
            instrument=instrument,
            order=next_order,
            **defaults,
        )


def remove_owner_watchlist_for_instrument(instrument: Instrument | int) -> None:
    owner_user_id = get_owner_user_id()
    instrument_id = instrument.id if isinstance(instrument, Instrument) else int(instrument)
    with suppress_schwab_subscription_signals():
        UserInstrumentWatchlistItem.objects.filter(user_id=owner_user_id, instrument_id=instrument_id).delete()


def upsert_quote_source_map(instrument: Instrument) -> None:
    """Publish the symbol->quote_source preference into Redis for fast gating."""

    from LiveData.shared.redis_client import live_data_redis

    sym = (instrument.symbol or "").strip().upper()
    if not sym:
        return

    key = getattr(settings, "INSTRUMENT_QUOTE_SOURCE_HASH", "instruments:quote_source")
    live_data_redis.client.hset(key, sym, (instrument.quote_source or "AUTO").upper())


def remove_quote_source_map(symbol: str) -> None:
    from LiveData.shared.redis_client import live_data_redis

    sym = (symbol or "").strip().upper()
    if not sym:
        return
    key = getattr(settings, "INSTRUMENT_QUOTE_SOURCE_HASH", "instruments:quote_source")
    live_data_redis.client.hdel(key, sym)
