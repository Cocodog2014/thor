from __future__ import annotations

from django.db import transaction

from LiveData.schwab.control_plane import publish_set
from Instruments.models import Instrument, UserInstrumentWatchlistItem
from Instruments.services.instrument_sync import get_owner_user_id


def _format_for_schwab(inst: Instrument) -> tuple[str, str] | tuple[None, None]:
        """Return (asset, symbol) formatted for Schwab streaming.

        Canonical DB convention:
            Instrument.symbol is stored without a leading '/'.

        Schwab convention (required by streamer):
            FUTURE symbols must be published with a leading '/'.
        """

        raw = (getattr(inst, "symbol", "") or "").strip().upper()
        base = raw.lstrip("/")
        if not base:
                return None, None

        if inst.asset_type == Instrument.AssetType.FUTURE:
                return "FUTURE", "/" + base

        # Everything else is treated as "equity" service for Schwab Level One.
        return "EQUITY", base


def sync_watchlist_to_schwab(user_id: int, *, publish_on_commit: bool = True) -> None:
    """Publish an authoritative Schwab subscription *set* based on the user's watchlist.

    Canonical source of truth is:
        UserInstrumentWatchlistItem(enabled=True, stream=True)

    This function does not write SchwabSubscription rows.
    """

    mode_cls = getattr(UserInstrumentWatchlistItem, "Mode", None)
    live_mode = getattr(mode_cls, "LIVE", "LIVE")
    global_mode = getattr(mode_cls, "GLOBAL", "GLOBAL")

    owner_user_id = int(get_owner_user_id())

    # Global list first (admin-managed), then user LIVE list.
    global_qs = (
        UserInstrumentWatchlistItem.objects.select_related("instrument")
        .filter(user_id=owner_user_id, mode=global_mode, enabled=True, stream=True, instrument__is_active=True)
        .order_by("order", "instrument__symbol")
    )

    user_qs = (
        UserInstrumentWatchlistItem.objects.select_related("instrument")
        .filter(user_id=user_id, mode=live_mode, enabled=True, stream=True, instrument__is_active=True)
        .order_by("order", "instrument__symbol")
    )

    # Stable merge without duplicates (global wins on order).
    seen_instrument_ids: set[int] = set()
    qs = []
    for item in list(global_qs) + list(user_qs):
        inst_id = int(getattr(item, "instrument_id", 0) or 0)
        if inst_id and inst_id in seen_instrument_ids:
            continue
        if inst_id:
            seen_instrument_ids.add(inst_id)
        qs.append(item)

    equities: list[str] = []
    futures: list[str] = []

    for item in qs:
        inst = item.instrument

        # Instruments can choose which feed owns the symbol.
        # If a symbol is set to TOS, do not subscribe it via Schwab.
        quote_source = (getattr(inst, "quote_source", None) or "AUTO").upper()
        if quote_source not in {"AUTO", "SCHWAB"}:
            continue

        asset, sym = _format_for_schwab(inst)
        if not asset or not sym:
            continue
        if asset == "FUTURE":
            futures.append(sym)
        else:
            equities.append(sym)

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

    def _publish() -> None:
        # Push sets to streamer for immediate convergence.
        publish_set(user_id=user_id, asset="EQUITY", symbols=equities)
        publish_set(user_id=user_id, asset="FUTURE", symbols=futures)

    if publish_on_commit:
        transaction.on_commit(_publish)
    else:
        _publish()


def sync_global_watchlist_to_schwab(*, publish_on_commit: bool = True) -> None:
    """When the GLOBAL list changes, resync all users with LIVE balances."""

    from ActAndPos.live.models import LiveBalance

    user_ids = list(LiveBalance.objects.values_list("user_id", flat=True).distinct())

    def _publish_all() -> None:
        for uid in user_ids:
            sync_watchlist_to_schwab(int(uid), publish_on_commit=False)

    if publish_on_commit:
        transaction.on_commit(_publish_all)
    else:
        _publish_all()
