# ThorTrading/intraday/supervisor.py

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from LiveData.shared.redis_client import live_data_redis
from ThorTrading.services.quotes import get_enriched_quotes_with_composite

from .redis_gateway import get_active_sessions

logger = logging.getLogger(__name__)


def _infer_asset_kind(row: Dict[str, Any]) -> str:
    """
    Returns "futures" or "equities".
    We avoid country/market logic completely.
    """
    inst = row.get("instrument") or {}
    sym = (inst.get("symbol") or row.get("symbol") or "").strip()

    # Prefer explicit hints if present
    asset = (
        row.get("asset_type")
        or inst.get("asset_type")
        or row.get("asset_class")
        or inst.get("asset_class")
        or ""
    )
    asset = str(asset).lower()

    if "future" in asset or "fut" in asset:
        return "futures"
    if "equity" in asset or "stock" in asset:
        return "equities"

    # Fallback: symbols that start with "/" often represent futures feeds
    if sym.startswith("/"):
        return "futures"

    return "equities"


def _normalize_symbol(row: Dict[str, Any]) -> Optional[str]:
    inst = row.get("instrument") or {}
    sym = inst.get("symbol") or row.get("symbol")
    if not sym:
        return None
    return str(sym).lstrip("/").upper()


def _make_tick(sym: str, row: Dict[str, Any], session_key: str, session_number: Optional[int]) -> Dict[str, Any]:
    return {
        "symbol": sym,
        "price": row.get("last"),
        "volume": row.get("volume"),
        "bid": row.get("bid"),
        "ask": row.get("ask"),
        "timestamp": row.get("timestamp"),
        "session_key": session_key,
        **({"session_number": session_number} if session_number is not None else {}),
    }


@dataclass
class IntradaySupervisor:
    """Thin supervisor used by the heartbeat scheduler.

    Responsibilities per tick:
      1) capture latest ticks into Redis (per active session)
      2) maintain current 1m bars in Redis
      3) enqueue closed 1m bars into Redis for later DB flush
    """

    include_equities: bool = True
    include_futures: bool = True

    def tick(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "captured": {"ticks": 0, "closed_bars": 0},
            "skipped": [],
            "error": None,
        }

        try:
            sessions = get_active_sessions()
            fut_key = sessions.futures
            eq_key = sessions.equities
            session_number = live_data_redis.get_active_session_number()

            if (self.include_futures and not fut_key) and (self.include_equities and not eq_key):
                result["skipped"].append({"reason": "no_active_sessions"})
                return result

            enriched, _meta = get_enriched_quotes_with_composite()

            captured_ticks = 0
            captured_closed = 0

            for row in enriched or []:
                sym = _normalize_symbol(row)
                if not sym:
                    continue

                kind = _infer_asset_kind(row)
                if kind == "futures":
                    if not self.include_futures or not fut_key:
                        continue
                    session_key = fut_key
                else:
                    if not self.include_equities or not eq_key:
                        continue
                    session_key = eq_key

                tick = _make_tick(sym, row, session_key=session_key, session_number=session_number)

                try:
                    # Latest tick cache (short TTL)
                    live_data_redis.set_tick(session_key, sym, tick, ttl=10)

                    # 1m bar maintenance
                    closed_bar, _current_bar = live_data_redis.upsert_current_bar_1m(session_key, sym, tick)
                    if closed_bar:
                        live_data_redis.enqueue_closed_bar(session_key, closed_bar)
                        captured_closed += 1

                    captured_ticks += 1
                except Exception:
                    # Best-effort: skip bad symbols but keep the loop alive
                    logger.exception("intraday_tick failed for %s (session=%s)", sym, session_key)
                    continue

            result["captured"]["ticks"] = captured_ticks
            result["captured"]["closed_bars"] = captured_closed
            return result

        except Exception as e:
            logger.exception("IntradaySupervisor.tick failed")
            result["error"] = str(e)
            return result


__all__ = ["IntradaySupervisor"]
