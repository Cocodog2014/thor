from __future__ import annotations

from django.db import transaction

from LiveData.schwab.control_plane import publish_set
from Instruments.models import Instrument, UserInstrumentWatchlistItem


def sync_watchlist_to_schwab(user_id: int) -> None:
    """Publish an authoritative Schwab subscription *set* based on the user's watchlist.

    Canonical source of truth is:
        UserInstrumentWatchlistItem(enabled=True, stream=True)

    This function does not write SchwabSubscription rows.
    """

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

        # Instruments can choose which feed owns the symbol.
        # If a symbol is set to TOS, do not subscribe it via Schwab.
        quote_source = (getattr(inst, "quote_source", None) or "AUTO").upper()
        if quote_source not in {"AUTO", "SCHWAB"}:
            continue
        if inst.asset_type == Instrument.AssetType.FUTURE:
            futures.append(symbol if symbol.startswith("/") else "/" + symbol.lstrip("/"))
        else:
            equities.append(symbol.lstrip("/"))

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

    def _on_commit() -> None:
        # Push sets to streamer for immediate convergence.
        publish_set(user_id=user_id, asset="EQUITY", symbols=equities)
        publish_set(user_id=user_id, asset="FUTURE", symbols=futures)

    transaction.on_commit(_on_commit)
