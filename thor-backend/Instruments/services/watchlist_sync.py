from __future__ import annotations

import json

from django.db import transaction

from LiveData.shared.redis_client import live_data_redis
from LiveData.schwab.models import SchwabSubscription
from Instruments.models import Instrument, UserInstrumentWatchlistItem


def _control_channel(user_id: int) -> str:
    return f"live_data:schwab:control:{user_id}"


def _publish_set(*, user_id: int, asset: str, symbols: list[str]) -> None:
    payload = {
        "action": "set",
        "asset": asset,
        "symbols": symbols,
    }
    live_data_redis.client.publish(_control_channel(int(user_id)), json.dumps(payload))


def sync_watchlist_to_schwab(user_id: int) -> None:
    """Ensure SchwabSubscription rows match the user's watchlist and push a 'set' to the streamer."""

    qs = (
        UserInstrumentWatchlistItem.objects.select_related("instrument")
        .filter(user_id=user_id, enabled=True, stream=True, instrument__is_active=True)
        .order_by("order", "instrument__symbol")
    )

    equities: list[str] = []
    futures: list[str] = []

    for item in qs:
        inst = item.instrument
        symbol = (inst.symbol or "").strip().upper()
        if not symbol:
            continue
        if inst.asset_type == Instrument.AssetType.FUTURE:
            futures.append(symbol)
        else:
            equities.append(symbol)

    # De-dupe stable
    def _dedupe(xs: list[str]) -> list[str]:
        seen = set()
        out: list[str] = []
        for x in xs:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    equities = _dedupe(equities)
    futures = _dedupe(futures)

    with transaction.atomic():
        # Persist desired set in DB so streamer can bootstrap from DB.
        SchwabSubscription.objects.filter(user_id=user_id, asset_type=SchwabSubscription.ASSET_EQUITY).exclude(
            symbol__in=equities
        ).delete()
        SchwabSubscription.objects.filter(user_id=user_id, asset_type=SchwabSubscription.ASSET_FUTURE).exclude(
            symbol__in=futures
        ).delete()

        for sym in equities:
            SchwabSubscription.objects.update_or_create(
                user_id=user_id,
                symbol=sym,
                asset_type=SchwabSubscription.ASSET_EQUITY,
                defaults={"enabled": True},
            )
        for sym in futures:
            SchwabSubscription.objects.update_or_create(
                user_id=user_id,
                symbol=sym,
                asset_type=SchwabSubscription.ASSET_FUTURE,
                defaults={"enabled": True},
            )

        def _on_commit() -> None:
            # Push sets to streamer for immediate convergence.
            _publish_set(user_id=user_id, asset="EQUITY", symbols=equities)
            _publish_set(user_id=user_id, asset="FUTURE", symbols=futures)

        transaction.on_commit(_on_commit)
