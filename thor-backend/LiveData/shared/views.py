from __future__ import annotations

import logging
import json
from typing import List
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .redis_client import live_data_redis

logger = logging.getLogger(__name__)


def _parse_symbols_param(raw: str | None) -> List[str]:
    if not raw:
        return []
    out: list[str] = []
    for s in raw.split(','):
        t = (s or '').strip().upper()
        if not t:
            continue
        if t.startswith('/'):
            t = '/' + t.lstrip('/')
        out.append(t)
    return out


@api_view(['GET'])
def get_quotes_snapshot(request):
    """Return latest quotes snapshot from Redis for specified symbols.

    Query params:
      - symbols: comma separated list, e.g. YM,ES,NQ,RTY,CL,SI,HG,GC,VX,DX,ZB

    Response:
      {
        "quotes": [ {symbol, bid, ask, last, volume, ...}, ...],
        "count": n,
        "source": "redis_snapshot"
      }
    """
    symbols = _parse_symbols_param(request.GET.get('symbols'))

    if not symbols:
        return Response({
            'quotes': [],
            'count': 0,
            'source': 'redis_snapshot',
            'note': 'No symbols specified'
        }, status=status.HTTP_200_OK)

    try:
        quotes = live_data_redis.get_latest_quotes(symbols)
        return Response({
            'quotes': quotes,
            'count': len(quotes),
            'source': 'redis_snapshot'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Snapshot read failed: {e}")
        return Response({'error': 'Snapshot read failed', 'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _wl_key(user_id: int, mode: str) -> str:
    return f"wl:{int(user_id)}:{mode}".lower()


def _wl_order_key(user_id: int, mode: str) -> str:
    return f"wl:{int(user_id)}:{mode}:order".lower()


def _normalize_symbol(sym: str) -> str | None:
    s = (sym or "").strip().upper()
    if not s:
        return None
    if s.startswith("/"):
        s = "/" + s.lstrip("/")
    return s


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_watchlist_quotes(request):
    """Return latest quotes snapshot for the user's Redis-mirrored watchlist.

    This endpoint does NOT hit the DB.

    Query params:
      - list: live | paper | both (default: live)
    """

    user_id = int(getattr(request.user, "id", 0) or 0)
    if not user_id:
        return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    which = (request.GET.get("list") or "live").strip().lower()
    if which not in {"live", "paper", "both"}:
        return Response(
            {"detail": "Invalid list", "valid": ["live", "paper", "both"]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    order_source = "set"

    def _read_ordered(mode: str) -> list[str]:
        key = _wl_order_key(user_id, mode)
        try:
            ordered = live_data_redis.client.zrange(key, 0, -1) or []
        except Exception:
            ordered = []
        out: list[str] = []
        seen_local: set[str] = set()
        for s in ordered:
            ns = _normalize_symbol(str(s))
            if not ns or ns in seen_local:
                continue
            seen_local.add(ns)
            out.append(ns)
        return out

    def _read_set(mode: str) -> set[str]:
        key = _wl_key(user_id, mode)
        raw = live_data_redis.client.smembers(key) or set()
        out: set[str] = set()
        for s in raw:
            ns = _normalize_symbol(str(s))
            if ns:
                out.add(ns)
        return out

    try:
        live_ordered = _read_ordered("live")
        paper_ordered = _read_ordered("paper")
        live_set = _read_set("live")
        paper_set = _read_set("paper")
    except Exception as exc:
        logger.error("Failed reading watchlist Redis keys: %s", exc)
        return Response(
            {"error": "Redis read failed", "detail": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def _finalize(ordered: list[str], members: set[str]) -> list[str]:
        # Keep ZSET order, but filter to membership set (in case of partial sync).
        out: list[str] = [s for s in ordered if s in members]
        # Add any set members missing from ZSET at end (stable alphabetical).
        missing = sorted([s for s in members if s not in set(out)])
        out.extend(missing)
        return out

    if which == "live":
        symbols = _finalize(live_ordered, live_set)
        order_source = "zset" if live_ordered else "set"
    elif which == "paper":
        symbols = _finalize(paper_ordered, paper_set)
        order_source = "zset" if paper_ordered else "set"
    else:
        # For both: keep LIVE first (in its order), then PAPER-only symbols.
        live_symbols = _finalize(live_ordered, live_set)
        paper_symbols = _finalize(paper_ordered, paper_set)
        paper_only = [s for s in paper_symbols if s not in set(live_symbols)]
        symbols = live_symbols + paper_only
        order_source = "zset" if (live_ordered or paper_ordered) else "set"

    if not symbols:
        return Response(
            {
                "quotes": [],
                "count": 0,
                "symbols": [],
                "order_source": order_source,
                "source": "redis_watchlist",
                "note": "Watchlist Redis set is empty (or not yet synced).",
            },
            status=status.HTTP_200_OK,
        )

    try:
        raws = live_data_redis.client.hmget(live_data_redis.LATEST_QUOTES_HASH, *symbols)
    except Exception as exc:
        logger.error("Failed hmget latest quotes: %s", exc)
        return Response(
            {"error": "Redis read failed", "detail": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    quotes: list[dict] = []
    missing: list[str] = []
    for sym, raw in zip(symbols, raws or []):
        if not raw:
            missing.append(sym)
            continue
        try:
            quotes.append(json.loads(raw))
        except Exception:
            # Corrupt or unexpected payload; treat as missing.
            missing.append(sym)

    return Response(
        {
            "quotes": quotes,
            "count": len(quotes),
            "symbols": symbols,
            "missing_symbols": missing,
            "order_source": order_source,
            "source": "redis_watchlist",
        },
        status=status.HTTP_200_OK,
    )
