from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, Optional

from django.db import transaction
from django.utils import timezone as dj_timezone

from Instruments.models.market_52w import Rolling52WeekStats
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Live52wKeys:
    symbol_key: str
    dirty_set_key: str


def _live_52w_keys(symbol: str, session_number: int) -> Live52wKeys:
    sym = (symbol or "").strip().upper()
    return Live52wKeys(
        symbol_key=f"live:52w:{sym}".lower(),
        dirty_set_key=f"live:52w:dirty:{int(session_number)}".lower(),
    )


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _to_utc_datetime(value: Any) -> datetime:
    """Best-effort conversion to aware UTC datetime."""

    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts = ts / 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)

    if isinstance(value, str):
        s = value.strip()
        if s:
            # ISO format
            try:
                if s.endswith("Z"):
                    s = s[:-1] + "+00:00"
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
            # numeric epoch
            try:
                ts = float(s)
                if ts > 1e12:
                    ts = ts / 1000.0
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                pass

    return datetime.now(timezone.utc)


def _to_utc_iso_z(dt: datetime) -> str:
    dt = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def _date_from_iso_or_date(value: Any) -> Optional[date]:
    """Parse Redis date field which may be 'YYYY-MM-DD' or ISO datetime."""

    if value in (None, ""):
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).date()

    s = str(value).strip()
    if not s:
        return None

    # date-only
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            return date.fromisoformat(s)
        except Exception:
            return None

    # ISO datetime
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).date()
    except Exception:
        return None


def seed_live_52w_all_symbols(*, session_number: int) -> int:
    """Seed Redis working copy for ALL symbols from Rolling52WeekStats.

    Key: live:52w:{SYMBOL} (hash)
    Fields: high_52w, high_52w_date, low_52w, low_52w_date, dirty=0,
            session_number, seeded_from_db_at

    Also clears dirty index set for this session_number.
    """

    sn = int(session_number)
    dirty_key = f"live:52w:dirty:{sn}".lower()

    try:
        live_data_redis.client.delete(dirty_key)
    except Exception:
        logger.debug("Failed clearing %s", dirty_key, exc_info=True)

    now_iso = _to_utc_iso_z(datetime.now(timezone.utc))

    qs = Rolling52WeekStats.objects.all().values(
        "symbol",
        "high_52w",
        "high_52w_date",
        "low_52w",
        "low_52w_date",
    )

    pipe = live_data_redis.client.pipeline(transaction=False)
    count = 0

    for row in qs.iterator(chunk_size=1000):
        sym = (row.get("symbol") or "").strip().upper()
        if not sym:
            continue

        high = row.get("high_52w")
        low = row.get("low_52w")
        high_date = row.get("high_52w_date")
        low_date = row.get("low_52w_date")

        def _date_to_iso_midnight(d: Any) -> Optional[str]:
            if d in (None, ""):
                return None
            if isinstance(d, date) and not isinstance(d, datetime):
                return f"{d.isoformat()}T00:00:00Z"
            parsed = _date_from_iso_or_date(d)
            return f"{parsed.isoformat()}T00:00:00Z" if parsed else None

        key = f"live:52w:{sym}".lower()
        pipe.hset(
            key,
            mapping={
                "high_52w": str(high) if high is not None else "",
                "high_52w_date": _date_to_iso_midnight(high_date) or "",
                "low_52w": str(low) if low is not None else "",
                "low_52w_date": _date_to_iso_midnight(low_date) or "",
                "dirty": "0",
                "session_number": str(sn),
                "seeded_from_db_at": now_iso,
            },
        )
        count += 1

    if count:
        try:
            pipe.execute()
        except Exception:
            logger.exception("Failed seeding 52w Redis snapshot (count=%s)", count)
            return 0

    return count


def seed_live_52w_symbol_from_db(*, session_number: int, symbol: str) -> bool:
    """Seed a single symbol working copy from DB into Redis."""

    sn = int(session_number)
    sym = (symbol or "").strip().upper()
    if not sym:
        return False

    row = Rolling52WeekStats.objects.filter(symbol=sym).values(
        "high_52w",
        "high_52w_date",
        "low_52w",
        "low_52w_date",
    ).first()

    now_iso = _to_utc_iso_z(datetime.now(timezone.utc))

    def _date_to_iso_midnight(d: Any) -> Optional[str]:
        if d in (None, ""):
            return None
        if isinstance(d, date) and not isinstance(d, datetime):
            return f"{d.isoformat()}T00:00:00Z"
        parsed = _date_from_iso_or_date(d)
        return f"{parsed.isoformat()}T00:00:00Z" if parsed else None

    key = f"live:52w:{sym}".lower()

    if not row:
        # No DB row: create a blank seeded row for safety.
        try:
            live_data_redis.client.hset(
                key,
                mapping={
                    "high_52w": "",
                    "high_52w_date": "",
                    "low_52w": "",
                    "low_52w_date": "",
                    "dirty": "0",
                    "session_number": str(sn),
                    "seeded_from_db_at": now_iso,
                },
            )
            return True
        except Exception:
            logger.debug("Failed seeding missing 52w symbol=%s", sym, exc_info=True)
            return False

    try:
        live_data_redis.client.hset(
            key,
            mapping={
                "high_52w": str(row.get("high_52w") or ""),
                "high_52w_date": _date_to_iso_midnight(row.get("high_52w_date")) or "",
                "low_52w": str(row.get("low_52w") or ""),
                "low_52w_date": _date_to_iso_midnight(row.get("low_52w_date")) or "",
                "dirty": "0",
                "session_number": str(sn),
                "seeded_from_db_at": now_iso,
            },
        )
        return True
    except Exception:
        logger.debug("Failed seeding 52w symbol=%s from DB", sym, exc_info=True)
        return False


def upsert_live_52w_on_price(
    *,
    session_number: int,
    symbol: str,
    price: Any,
    asof_ts: Any = None,
) -> Optional[Dict[str, Any]]:
    """Compare incoming price to Redis 52w extremes, update if needed.

    Implements:
    - Ensure correct session snapshot (seed from DB if missing/mismatched)
    - Compare/update high_52w/low_52w
    - Mark dirty + add to per-session dirty set

    Returns snapshot dict ONLY when an extreme changed (for WS broadcast).
    """

    sn = int(session_number)
    sym = (symbol or "").strip().upper()
    if not sym:
        return None

    px = _to_decimal(price)
    if px is None:
        return None

    dt = _to_utc_datetime(asof_ts)
    asof_iso = _to_utc_iso_z(dt)

    keys = _live_52w_keys(sym, sn)

    try:
        sess_s, high_s, low_s, high_dt_s, low_dt_s, dirty_s = live_data_redis.client.hmget(
            keys.symbol_key,
            "session_number",
            "high_52w",
            "low_52w",
            "high_52w_date",
            "low_52w_date",
            "dirty",
        )
    except Exception:
        sess_s = high_s = low_s = high_dt_s = low_dt_s = dirty_s = None

    # Safety net for restarts: seed if missing or wrong session.
    needs_seed = False
    if not sess_s:
        needs_seed = True
    else:
        try:
            needs_seed = int(sess_s) != sn
        except Exception:
            needs_seed = True

    if needs_seed:
        try:
            seed_live_52w_symbol_from_db(session_number=sn, symbol=sym)
            sess_s, high_s, low_s, high_dt_s, low_dt_s, dirty_s = live_data_redis.client.hmget(
                keys.symbol_key,
                "session_number",
                "high_52w",
                "low_52w",
                "high_52w_date",
                "low_52w_date",
                "dirty",
            )
        except Exception:
            logger.debug("Failed reseeding live 52w for %s", sym, exc_info=True)

    high_v = _to_decimal(high_s)
    low_v = _to_decimal(low_s)

    changed = False
    mapping: Dict[str, str] = {}

    if high_v is None or px > high_v:
        mapping["high_52w"] = str(px)
        mapping["high_52w_date"] = asof_iso
        changed = True

    if low_v is None or px < low_v:
        mapping["low_52w"] = str(px)
        mapping["low_52w_date"] = asof_iso
        changed = True

    if not changed:
        return None

    mapping["dirty"] = "1"

    try:
        pipe = live_data_redis.client.pipeline(transaction=False)
        pipe.hset(keys.symbol_key, mapping=mapping)
        pipe.sadd(keys.dirty_set_key, sym)
        pipe.execute()
    except Exception:
        logger.debug("Failed writing live 52w update for %s", sym, exc_info=True)
        return None

    # Return a WS-friendly snapshot.
    try:
        high_now, high_dt_now, low_now, low_dt_now = live_data_redis.client.hmget(
            keys.symbol_key, "high_52w", "high_52w_date", "low_52w", "low_52w_date"
        )
    except Exception:
        high_now, high_dt_now, low_now, low_dt_now = mapping.get("high_52w"), mapping.get("high_52w_date"), mapping.get(
            "low_52w"
        ), mapping.get("low_52w_date")

    return {
        "symbol": sym,
        "session_number": sn,
        "high_52w": high_now or None,
        "high_52w_date": high_dt_now or None,
        "low_52w": low_now or None,
        "low_52w_date": low_dt_now or None,
    }


def finalize_live_52w_to_db(*, session_number: int) -> int:
    """Write dirty 52w updates from Redis back to DB once per session_number."""

    sn = int(session_number)
    dirty_key = f"live:52w:dirty:{sn}".lower()

    try:
        symbols = live_data_redis.client.smembers(dirty_key) or set()
    except Exception:
        logger.debug("Failed reading %s", dirty_key, exc_info=True)
        return 0

    symbols = {str(s).strip().upper() for s in symbols if s}
    if not symbols:
        try:
            live_data_redis.client.delete(dirty_key)
        except Exception:
            pass
        return 0

    updated = 0

    with transaction.atomic():
        for sym in sorted(symbols):
            key = f"live:52w:{sym}".lower()
            try:
                high_s, high_dt_s, low_s, low_dt_s = live_data_redis.client.hmget(
                    key, "high_52w", "high_52w_date", "low_52w", "low_52w_date"
                )
            except Exception:
                continue

            high_v = _to_decimal(high_s)
            low_v = _to_decimal(low_s)
            high_d = _date_from_iso_or_date(high_dt_s)
            low_d = _date_from_iso_or_date(low_dt_s)

            if high_v is None or low_v is None or high_d is None or low_d is None:
                continue

            Rolling52WeekStats.objects.update_or_create(
                symbol=sym,
                defaults={
                    "high_52w": high_v,
                    "high_52w_date": high_d,
                    "low_52w": low_v,
                    "low_52w_date": low_d,
                },
            )
            updated += 1

            # Clear dirty flag in the symbol hash.
            try:
                live_data_redis.client.hset(key, mapping={"dirty": "0"})
            except Exception:
                pass

    try:
        live_data_redis.client.delete(dirty_key)
    except Exception:
        logger.debug("Failed deleting %s", dirty_key, exc_info=True)

    return updated
