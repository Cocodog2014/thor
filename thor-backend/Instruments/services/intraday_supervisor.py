from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import time

from LiveData.shared.redis_client import live_data_redis
from Instruments.services.intraday_flush import flush_closed_bars

logger = logging.getLogger(__name__)


def _infer_asset_kind(row: Dict[str, Any]) -> str:
    """Return "futures" or "equities" based on quote metadata."""

    sym = (row.get("symbol") or "").strip()

    asset = row.get("asset_type") or row.get("asset_class") or ""
    asset = str(asset).lower()

    if "future" in asset or "fut" in asset:
        return "futures"
    if "equity" in asset or "stock" in asset:
        return "equities"

    if sym.startswith("/"):
        return "futures"

    return "equities"


def _normalize_symbol(row: Dict[str, Any]) -> Optional[str]:
    sym = row.get("symbol")
    if not sym:
        return None
    return str(sym).lstrip("/").upper()


def _active_symbols(max_age_seconds: int = 60, limit: int = 5000) -> list[str]:
    now = int(time.time())
    min_score = now - int(max_age_seconds)
    try:
        symbols = live_data_redis.client.zrevrangebyscore(
            live_data_redis.ACTIVE_QUOTES_ZSET,
            max=now,
            min=min_score,
            start=0,
            num=int(limit),
        )
        return [str(s).lstrip("/").upper() for s in symbols if s]
    except Exception:
        return []


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
    """1-second tick supervisor that aggregates Redis quotes into 1-minute OHLCV.

    Lives in Instruments because it writes Instruments DB truth tables.
    LiveData remains responsible only for streaming + Redis publishing.
    """

    include_equities: bool = True
    include_futures: bool = True

    def tick(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "captured": {"ticks": 0, "closed_bars": 0},
            "flushed": {"equities": 0, "futures": 0},
            "skipped": [],
            "error": None,
        }

        try:
            fut_key = live_data_redis.get_active_session_key(asset_type="futures")
            eq_key = live_data_redis.get_active_session_key(asset_type="equities")
            session_number = live_data_redis.get_active_session_number()

            if (self.include_futures and not fut_key) and (self.include_equities and not eq_key):
                result["skipped"].append({"reason": "no_active_sessions"})
                return result

            symbols = _active_symbols(max_age_seconds=60, limit=5000)
            enriched = live_data_redis.get_latest_quotes(symbols) if symbols else []

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
                    live_data_redis.set_tick(session_key, sym, tick, ttl=10)

                    closed_bar, _current_bar = live_data_redis.upsert_current_bar_1m(session_key, sym, tick)
                    if closed_bar:
                        live_data_redis.enqueue_closed_bar(session_key, closed_bar)
                        captured_closed += 1

                    captured_ticks += 1
                except Exception:
                    logger.exception("intraday_tick failed for %s (session=%s)", sym, session_key)
                    continue

            result["captured"]["ticks"] = captured_ticks
            result["captured"]["closed_bars"] = captured_closed

            try:
                if self.include_futures and fut_key:
                    result["flushed"]["futures"] = int(flush_closed_bars(fut_key, batch_size=500, max_batches=1) or 0)
                if self.include_equities and eq_key:
                    result["flushed"]["equities"] = int(flush_closed_bars(eq_key, batch_size=500, max_batches=1) or 0)
            except Exception:
                logger.exception("intraday_flush failed")

            return result

        except Exception as e:
            logger.exception("IntradaySupervisor.tick failed")
            result["error"] = str(e)
            return result


__all__ = ["IntradaySupervisor"]
