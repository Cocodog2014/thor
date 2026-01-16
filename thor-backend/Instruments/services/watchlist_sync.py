from __future__ import annotations

from django.db import transaction
import os

from LiveData.schwab.control_plane import publish_set
from Instruments.models import Instrument, UserInstrumentWatchlistItem
from Instruments.services.watchlist_redis_sets import (
    get_watchlist_union_from_redis,
    is_watchlists_hydrated,
    sync_watchlist_sets_to_redis,
)


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

        # Canonical convention in Thor: indexes are stored with a leading '$' (e.g. $DXY).
        # Schwab streaming should receive '$' for indexes so it recognizes the asset as an index.
        # If you need legacy behavior, set THOR_SCHWAB_INDEX_STRIP_DOLLAR=1.
        if inst.asset_type == Instrument.AssetType.INDEX or base.startswith("$"):
            strip_dollar = os.getenv("THOR_SCHWAB_INDEX_STRIP_DOLLAR", "").strip().lower() in {"1", "true", "yes", "on"}
            if strip_dollar:
                base = base.lstrip("$")
            if not base:
                return None, None

        # Everything else is treated as "equity" service for Schwab Level One.
        return "EQUITY", base


def sync_watchlist_to_schwab(user_id: int, *, publish_on_commit: bool = True) -> None:
    """Publish an authoritative Schwab subscription *set* based on the user's watchlist.

    Canonical source of truth is:
        UserInstrumentWatchlistItem(enabled=True, stream=True)

    This function does not write SchwabSubscription rows.
    """

    # Prefer Redis union (runtime truth): union(paper, live)
    # This avoids subscription thrash when a symbol moves between modes.
    union_symbols: list[str] = []
    try:
        union_symbols = get_watchlist_union_from_redis(user_id=int(user_id))
    except Exception:
        union_symbols = []

    # Cold cache fallback: if Redis isn't hydrated yet, build it from DB.
    if not union_symbols and not is_watchlists_hydrated(user_id=int(user_id)):
        try:
            sync_watchlist_sets_to_redis(int(user_id))
            union_symbols = get_watchlist_union_from_redis(user_id=int(user_id))
        except Exception:
            union_symbols = []

    # If still empty, publish empty desired sets (unsubscribe all).
    if not union_symbols:
        equities: list[str] = []
        futures: list[str] = []
    else:
        # Query instruments for symbols. DB convention: futures are stored without leading '/'.
        query_symbols: set[str] = set()
        for s in union_symbols:
            ss = (s or "").strip().upper()
            if not ss:
                continue
            if ss.startswith("/"):
                query_symbols.add(ss.lstrip("/"))
            else:
                query_symbols.add(ss)
            if ss.startswith("$"):
                query_symbols.add(ss.lstrip("$"))

        instruments = list(
            Instrument.objects.filter(
                symbol__in=sorted(query_symbols),
                is_active=True,
            )
        )

        equities = []
        futures = []

        for inst in instruments:
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
