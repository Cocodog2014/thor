from __future__ import annotations

import logging
from typing import Iterable

from Instruments.models import UserInstrumentWatchlistItem
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


def _wl_key(user_id: int, mode: str) -> str:
    return f"wl:{int(user_id)}:{mode}".lower()


def _wl_order_key(user_id: int, mode: str) -> str:
    return f"wl:{int(user_id)}:{mode}:order".lower()


def _wl_hydrated_key(user_id: int) -> str:
    # Sentinel to distinguish "cold cache" (unknown) from "known empty".
    # When present, it means Redis watchlist keys are the current truth even if empty.
    return f"wl:{int(user_id)}:hydrated".lower()


def is_watchlists_hydrated(*, user_id: int) -> bool:
    try:
        return bool(live_data_redis.client.exists(_wl_hydrated_key(int(user_id))))
    except Exception:
        return False


def mark_watchlists_hydrated(*, user_id: int, ttl_seconds: int = 6 * 60 * 60) -> None:
    try:
        live_data_redis.client.set(_wl_hydrated_key(int(user_id)), "1", ex=int(ttl_seconds))
    except Exception:
        logger.debug("Failed marking watchlists hydrated for user_id=%s", user_id, exc_info=True)


def _norm_symbols(symbols: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    for raw in symbols:
        sym = (raw or "").strip().upper()
        if not sym:
            continue
        if sym.startswith("/"):
            sym = "/" + sym.lstrip("/")
        if sym in seen:
            continue
        seen.add(sym)
        out.append(sym)

    return out


def sync_watchlist_sets_to_redis(user_id: int) -> None:
    """Mirror DB watchlists to per-user Redis sets.

    Writes:
      - wl:{user_id}:paper
      - wl:{user_id}:live

    A symbol may exist in one set, the other, or both.
    This function intentionally does not read from Redis and does not attempt
    partial updates; it rewrites the sets from DB truth.
    """

    mode_cls = getattr(UserInstrumentWatchlistItem, "Mode", None)
    paper = getattr(mode_cls, "PAPER", "PAPER")
    live = getattr(mode_cls, "LIVE", "LIVE")

    try:
        qs = (
            UserInstrumentWatchlistItem.objects.select_related("instrument")
            .filter(user_id=int(user_id), enabled=True, instrument__is_active=True)
            .values_list("mode", "instrument__symbol", "order")
        )
    except Exception:
        logger.exception("Failed loading watchlist rows for Redis sync user_id=%s", user_id)
        return

    paper_symbols: list[str] = []
    live_symbols: list[str] = []

    paper_order: dict[str, float] = {}
    live_order: dict[str, float] = {}

    for mode, sym, order in qs:
        if not sym:
            continue

        sym_norm = _normalize_symbol(sym)
        if not sym_norm:
            continue

        # Best-effort score for ordering. If missing, push to end.
        try:
            score = float(order)
        except Exception:
            score = 1e12

        if mode == paper:
            paper_symbols.append(sym_norm)
            paper_order[sym_norm] = score
        if mode == live:
            live_symbols.append(sym_norm)
            live_order[sym_norm] = score

    paper_symbols = _norm_symbols(paper_symbols)
    live_symbols = _norm_symbols(live_symbols)

    # Ensure ZSETs only contain members that are in the set (after de-dupe).
    paper_order = {s: paper_order.get(s, 1e12) for s in paper_symbols}
    live_order = {s: live_order.get(s, 1e12) for s in live_symbols}

    paper_key = _wl_key(user_id, "paper")
    live_key = _wl_key(user_id, "live")
    paper_order_key = _wl_order_key(user_id, "paper")
    live_order_key = _wl_order_key(user_id, "live")
    hydrated_key = _wl_hydrated_key(user_id)

    try:
        pipe = live_data_redis.client.pipeline(transaction=False)
        pipe.delete(paper_key)
        pipe.delete(live_key)
        pipe.delete(paper_order_key)
        pipe.delete(live_order_key)
        if paper_symbols:
            pipe.sadd(paper_key, *paper_symbols)
            pipe.zadd(paper_order_key, paper_order)
        if live_symbols:
            pipe.sadd(live_key, *live_symbols)
            pipe.zadd(live_order_key, live_order)

        # Mark that watchlists have been synced from DB -> Redis, even if empty.
        # This prevents repeated DB reads on every websocket connect for users with empty lists.
        pipe.set(hydrated_key, "1", ex=6 * 60 * 60)
        pipe.execute()
    except Exception:
        logger.exception("Failed writing watchlist Redis sets for user_id=%s", user_id)


def set_watchlist_order_in_redis(*, user_id: int, mode: str, symbols: list[str]) -> dict:
    """Rewrite watchlist order ZSET in Redis without touching the DB.

    Requires the membership SET `wl:{user_id}:{mode}` to already exist.

    Args:
        user_id: Authenticated user id.
        mode: "live" or "paper".
        symbols: Desired order (best-effort). Unknown/non-member symbols are ignored.

    Returns a small summary dict with final symbols and counts.
    """

    mode_norm = (mode or "").strip().lower()
    if mode_norm not in {"live", "paper"}:
        raise ValueError("mode must be 'live' or 'paper'")

    set_key = _wl_key(user_id, mode_norm)
    order_key = _wl_order_key(user_id, mode_norm)

    # Membership truth comes from the SET.
    members_raw = live_data_redis.client.smembers(set_key) or set()
    members: set[str] = set()
    for s in members_raw:
        ns = _normalize_symbol(str(s))
        if ns:
            members.add(ns)
    if not members:
        return {
            "mode": mode_norm,
            "symbols": [],
            "count": 0,
            "note": f"Redis set {set_key} is empty or missing",
        }

    desired: list[str] = []
    seen: set[str] = set()
    for s in symbols or []:
        ns = _normalize_symbol(str(s))
        if not ns or ns in seen:
            continue
        seen.add(ns)
        if ns in members:
            desired.append(ns)

    # Append any remaining members not provided.
    remaining = sorted([m for m in members if m not in set(desired)])
    final = desired + remaining

    mapping = {sym: float(i) for i, sym in enumerate(final)}
    pipe = live_data_redis.client.pipeline(transaction=False)
    pipe.delete(order_key)
    if mapping:
        pipe.zadd(order_key, mapping)
    pipe.execute()

    return {
        "mode": mode_norm,
        "symbols": final,
        "count": len(final),
        "order_key": order_key,
        "set_key": set_key,
    }


def _normalize_symbol(sym: str) -> str | None:
    s = (sym or "").strip().upper()
    if not s:
        return None
    if s.startswith("/"):
        s = "/" + s.lstrip("/")
    return s


def get_watchlist_symbols_from_redis(*, user_id: int, mode: str) -> list[str] | None:
    """Return ordered watchlist symbols from Redis.

    If the membership SET is missing/empty, returns None.
    Ordering comes from the ZSET when present.
    """

    mode_norm = (mode or "").strip().lower()
    if mode_norm not in {"live", "paper"}:
        return None

    set_key = _wl_key(user_id, mode_norm)
    order_key = _wl_order_key(user_id, mode_norm)

    try:
        members_raw = live_data_redis.client.smembers(set_key) or set()
    except Exception:
        logger.exception("Failed reading Redis watchlist set %s", set_key)
        return None

    members: set[str] = set()
    for s in members_raw:
        ns = _normalize_symbol(str(s))
        if ns:
            members.add(ns)

    if not members:
        return None

    ordered: list[str] = []
    try:
        if int(live_data_redis.client.zcard(order_key) or 0) > 0:
            z = live_data_redis.client.zrange(order_key, 0, -1) or []
            for s in z:
                ns = _normalize_symbol(str(s))
                if ns and ns in members:
                    ordered.append(ns)
    except Exception:
        logger.debug("Failed reading Redis watchlist order %s", order_key, exc_info=True)

    # Fallback: stable order (alpha) plus any un-ordered members.
    remaining = sorted([m for m in members if m not in set(ordered)])
    return ordered + remaining


def get_watchlists_snapshot_from_redis(*, user_id: int) -> dict[str, list[str]]:
    """Return both live and paper watchlists from Redis (empty lists if missing)."""
    return {
        "paper": get_watchlist_symbols_from_redis(user_id=user_id, mode="paper") or [],
        "live": get_watchlist_symbols_from_redis(user_id=user_id, mode="live") or [],
    }


def build_watchlist_items_payload(*, user_id: int, mode_norm: str, db_mode: str) -> list[dict] | None:
    """Build an API-compatible items list from Redis membership/order."""
    symbols = get_watchlist_symbols_from_redis(user_id=user_id, mode=mode_norm)
    if symbols is None:
        return None

    items: list[dict] = []
    for i, sym in enumerate(symbols):
        items.append(
            {
                "instrument": {"symbol": sym},
                "enabled": True,
                "stream": True,
                "mode": db_mode,
                "order": i,
            }
        )
    return items
