from __future__ import annotations

from django.db import transaction
import os

from LiveData.schwab.control_plane import publish_set
from Instruments.models import Instrument, UserInstrumentWatchlistItem


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

    mode_cls = getattr(UserInstrumentWatchlistItem, "Mode", None)
    paper_mode = getattr(mode_cls, "PAPER", "PAPER")
    live_mode = getattr(mode_cls, "LIVE", "LIVE")

    user_qs = (
        UserInstrumentWatchlistItem.objects.select_related("instrument")
        # Streamer subscribes to the union of LIVE + PAPER so PAPER lists also get live quotes.
        .filter(user_id=user_id, mode__in=[paper_mode, live_mode], enabled=True, stream=True, instrument__is_active=True)
        .order_by("order", "instrument__symbol")
    )

    qs = list(user_qs)

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
