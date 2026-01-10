from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional

import time

from LiveData.shared.redis_client import live_data_redis
from Instruments.services.intraday_flush import flush_closed_bars
from Instruments.models.market_24h import MarketTrading24Hour
from Instruments.services.market_52w_live import finalize_live_52w_to_db, seed_live_52w_all_symbols
from Instruments.services.market_52w_live import upsert_live_52w_on_price

from api.websocket.broadcast import broadcast_to_websocket_sync

logger = logging.getLogger(__name__)


_LAST_UTC_SESSION_NUMBER_KEY = "intraday:last_utc_session_number"
_LAST_52W_RECOMPUTE_DAY_KEY = "intraday:last_52w_recompute_day"


def _session_date_from_session_number(session_number: int) -> date | None:
    """Best-effort parse YYYYMMDD session_number into a date."""

    try:
        s = str(int(session_number))
    except Exception:
        return None
    if len(s) != 8:
        return None
    try:
        return date(int(s[0:4]), int(s[4:6]), int(s[6:8]))
    except Exception:
        return None


def _maybe_recompute_52w_for_day(asof_date: date) -> None:
    """Recompute rolling 52w highs/lows once per UTC day.

    Guarded by a Redis key so restarts don't rerun the expensive recompute.
    """

    try:
        last_day_raw = live_data_redis.client.get(_LAST_52W_RECOMPUTE_DAY_KEY)
        last_day = str(last_day_raw).strip() if last_day_raw else ""
    except Exception:
        last_day = ""

    asof_key = asof_date.isoformat()
    if last_day == asof_key:
        return

    from Instruments.services.market_52w_recompute import recompute_rolling_52w_from_24h

    result = recompute_rolling_52w_from_24h(asof_date=asof_date, window_days=365)

    logger.info(
        "52w recompute done: asof=%s window_days=%s symbols_seen=%s updated=%s skipped_no_data=%s",
        result.asof_date,
        result.window_days,
        result.symbols_seen,
        result.updated_rows,
        result.skipped_no_data,
    )

    try:
        live_data_redis.client.set(_LAST_52W_RECOMPUTE_DAY_KEY, asof_key, ex=7 * 24 * 3600)
    except Exception:
        logger.debug("Failed to set %s", _LAST_52W_RECOMPUTE_DAY_KEY, exc_info=True)


def _finalize_previous_session_if_rolled_over() -> None:
    """Finalize MarketTrading24Hour for the previous UTC day when day rolls over."""

    # Prefer the shared session_number published by GlobalMarkets -> LiveData.
    current_sn = None
    try:
        current_sn = live_data_redis.get_active_session_number()
    except Exception:
        current_sn = None

    if current_sn is None:
        current_sn = int(datetime.now(timezone.utc).strftime("%Y%m%d"))
    else:
        current_sn = int(current_sn)
    try:
        raw_prev = live_data_redis.client.get(_LAST_UTC_SESSION_NUMBER_KEY)
        prev_sn = int(raw_prev) if raw_prev not in (None, "") else None
    except Exception:
        prev_sn = None

    if prev_sn is None:
        # First boot (or Redis got cleared): ensure 52w working copy exists for today.
        # Also recompute yesterday once (guarded) so 52w doesn't get stuck stale after restarts.
        try:
            yesterday = (_session_date_from_session_number(current_sn) or datetime.now(timezone.utc).date()) - timedelta(days=1)
            _maybe_recompute_52w_for_day(yesterday)
        except Exception:
            logger.exception("Failed daily 52w recompute on boot")
        try:
            seed_live_52w_all_symbols(session_number=current_sn)
        except Exception:
            logger.exception("Failed seeding live 52w snapshot for session_number=%s", current_sn)

    if prev_sn is not None and prev_sn != current_sn:
        try:
            MarketTrading24Hour.objects.filter(session_number=prev_sn, finalized=False).update(finalized=True)
        except Exception:
            logger.exception("Failed finalizing MarketTrading24Hour for session_number=%s", prev_sn)

        # Finalize 52w once per session_number (DB write only for dirty symbols), then seed new session.
        try:
            finalize_live_52w_to_db(session_number=prev_sn)
        except Exception:
            logger.exception("Failed finalizing live 52w to DB for session_number=%s", prev_sn)

        # Daily rolling 52w recompute from 24h history (fixes expired extremes).
        try:
            asof = _session_date_from_session_number(prev_sn) or (datetime.now(timezone.utc).date() - timedelta(days=1))
            _maybe_recompute_52w_for_day(asof)
        except Exception:
            logger.exception("Failed daily 52w recompute for prev session_number=%s", prev_sn)
        try:
            seed_live_52w_all_symbols(session_number=current_sn)
        except Exception:
            logger.exception("Failed seeding live 52w snapshot for session_number=%s", current_sn)

    try:
        live_data_redis.client.set(_LAST_UTC_SESSION_NUMBER_KEY, str(current_sn), ex=7 * 24 * 3600)
    except Exception:
        logger.debug("Failed to set %s", _LAST_UTC_SESSION_NUMBER_KEY, exc_info=True)


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


def _make_tick(
    sym: str,
    row: Dict[str, Any],
    *,
    routing_key: str,
    session_number: Optional[int],
    session_date: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "symbol": sym,
        "price": row.get("last"),
        "volume": row.get("volume"),
        "bid": row.get("bid"),
        "ask": row.get("ask"),
        "ts": row.get("ts"),
        "timestamp": row.get("timestamp"),
        "routing_key": routing_key,
        **({"session_date": session_date} if session_date else {}),
        **({"session_number": session_number} if session_number is not None else {}),
    }


def _utc_day_session(now: datetime | None = None) -> tuple[str, int]:
    """Global intraday session keyed by UTC trading day.

    Boundary: 00:00 UTC.
    session_date: YYYY-MM-DD
    session_number: YYYYMMDD (int)
    """

    dt = now.astimezone(timezone.utc) if now is not None else datetime.now(timezone.utc)
    session_key = dt.date().isoformat()
    session_number = int(dt.strftime("%Y%m%d"))
    return session_key, session_number


def _utc_day_session_from_timestamp(value: Any) -> tuple[str, int]:
    """Compute UTC-day session key/number from a timestamp-like value.

    Accepts epoch seconds/ms, ISO strings, or datetimes.
    Falls back to server time when unparseable.
    """

    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return _utc_day_session(dt)

    if isinstance(value, (int, float)):
        ts = float(value)
        # Heuristic: treat very large values as milliseconds.
        if ts > 1e12:
            ts = ts / 1000.0
        try:
            return _utc_day_session(datetime.fromtimestamp(ts, tz=timezone.utc))
        except Exception:
            return _utc_day_session()

    if isinstance(value, str):
        s = value.strip()
        if s:
            try:
                if s.endswith("Z"):
                    s = s[:-1] + "+00:00"
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return _utc_day_session(dt)
            except Exception:
                pass
            try:
                ts = float(s)
                if ts > 1e12:
                    ts = ts / 1000.0
                return _utc_day_session(datetime.fromtimestamp(ts, tz=timezone.utc))
            except Exception:
                pass

    return _utc_day_session()


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
            _finalize_previous_session_if_rolled_over()
            symbols = _active_symbols(max_age_seconds=60, limit=5000)
            enriched = live_data_redis.get_latest_quotes(symbols) if symbols else []

            captured_ticks = 0
            captured_closed = 0
            session_keys_seen: set[str] = set()

            for row in enriched or []:
                sym = _normalize_symbol(row)
                if not sym:
                    continue

                kind = _infer_asset_kind(row)
                if kind == "futures":
                    if not self.include_futures:
                        continue
                else:
                    if not self.include_equities:
                        continue

                # Prefer the shared session routing snapshot so Schwab streaming + intraday supervisor
                # write to the same namespaces. Fall back to timestamp-based UTC day.
                session_number = None
                try:
                    asset_hint = "FUTURES" if kind == "futures" else "EQUITIES"
                    session_number = live_data_redis.get_active_session_number(asset_type=asset_hint)
                except Exception:
                    session_number = None

                if session_number is None:
                    session_date, session_number = _utc_day_session_from_timestamp(
                        row.get("timestamp") or row.get("ts")
                    )
                else:
                    session_number = int(session_number)
                    s = str(session_number)
                    session_date = f"{s[0:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 else None

                # Global routing: bars are keyed by broad asset class only.
                # session_number is carried as metadata for 24h/52w logic.
                routing_key = "futures" if kind == "futures" else "equities"
                session_keys_seen.add(routing_key)

                price = row.get("last")
                if price is None:
                    price = row.get("bid") or row.get("ask")

                # Live 52w extremes in Redis + WS broadcast for React.
                try:
                    snap_52w = upsert_live_52w_on_price(
                        session_number=session_number,
                        symbol=sym,
                        price=price,
                        asof_ts=row.get("timestamp") or row.get("ts"),
                    )
                    if snap_52w:
                        broadcast_to_websocket_sync(
                            channel_layer=None,
                            message={"type": "market.52w", "data": snap_52w},
                        )
                except Exception:
                    logger.debug("live52w update failed for %s", sym, exc_info=True)

                # Live 24h snapshot in Redis + WS broadcast for React.
                try:
                    snap = live_data_redis.upsert_live_24h_snapshot(
                        session_number,
                        sym,
                        price=price,
                        volume=row.get("volume"),
                    )
                    if snap:
                        broadcast_to_websocket_sync(
                            channel_layer=None,
                            message={"type": "market.24h", "data": snap},
                        )
                except Exception:
                    logger.debug("live24h update failed for %s", sym, exc_info=True)

                tick = _make_tick(
                    sym,
                    row,
                    routing_key=routing_key,
                    session_number=session_number,
                    session_date=session_date,
                )

                try:
                    live_data_redis.set_tick(routing_key, sym, tick, ttl=10)

                    closed_bar, _current_bar = live_data_redis.upsert_current_bar_1m(routing_key, sym, tick)
                    if closed_bar:
                        live_data_redis.enqueue_closed_bar(routing_key, closed_bar)
                        captured_closed += 1

                    captured_ticks += 1
                except Exception:
                    logger.exception("intraday_tick failed for %s (session=%s)", sym, routing_key)
                    continue

            result["captured"]["ticks"] = captured_ticks
            result["captured"]["closed_bars"] = captured_closed

            try:
                flushed = {"equities": 0, "futures": 0}
                for key in sorted(session_keys_seen):
                    inserted = int(flush_closed_bars(key, batch_size=500, max_batches=1) or 0)
                    if key in flushed:
                        flushed[key] += inserted

                if self.include_futures:
                    result["flushed"]["futures"] = flushed["futures"]
                if self.include_equities:
                    result["flushed"]["equities"] = flushed["equities"]
            except Exception:
                logger.exception("intraday_flush failed")

            return result

        except Exception as e:
            logger.exception("IntradaySupervisor.tick failed")
            result["error"] = str(e)
            return result


__all__ = ["IntradaySupervisor"]
