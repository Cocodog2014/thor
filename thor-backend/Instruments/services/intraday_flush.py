from __future__ import annotations

import logging
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import Dict, Iterable, List, Optional, Tuple

from django.db import transaction
from django.db.models import Max, Min, Sum

from Instruments.models.intraday import InstrumentIntraday
from Instruments.models.market_24h import MarketTrading24Hour
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


def _parse_session_number(routing_key: str) -> Optional[int]:
    try:
        return int(str(routing_key).strip())
    except Exception:
        return None


def _session_date_from_number(session_number: int) -> Optional[date]:
    try:
        s = str(int(session_number))
        if len(s) != 8:
            return None
        return date(int(s[0:4]), int(s[4:6]), int(s[6:8]))
    except Exception:
        return None


def _prev_session_number(session_number: int) -> Optional[int]:
    d = _session_date_from_number(session_number)
    if d is None:
        return None
    prev = d - timedelta(days=1)
    return int(prev.strftime("%Y%m%d"))


def _iter_unique_symbols(rows: Iterable[InstrumentIntraday]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for r in rows:
        sym = (getattr(r, "symbol", None) or "").strip().upper()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    return out


def _recompute_market_trading_24h_for_symbols(session_number: int, symbols: list[str]) -> int:
    """Recompute MarketTrading24Hour for (session_number, symbol) from InstrumentIntraday."""

    session_date = _session_date_from_number(session_number)
    if session_date is None or not symbols:
        return 0

    start = datetime(session_date.year, session_date.month, session_date.day, tzinfo=dt_timezone.utc)
    end = start + timedelta(days=1)

    updated = 0
    prev_sn = _prev_session_number(session_number)

    for symbol in symbols:
        base_qs = InstrumentIntraday.objects.filter(
            symbol=symbol,
            timestamp_minute__gte=start,
            timestamp_minute__lt=end,
        )

        first = base_qs.order_by("timestamp_minute").values_list("open_1m", flat=True).first()
        last = base_qs.order_by("-timestamp_minute").values_list("close_1m", flat=True).first()

        agg = base_qs.aggregate(
            high_24h=Max("high_1m"),
            low_24h=Min("low_1m"),
            volume_24h=Sum("volume_1m"),
        )

        high_24h = agg.get("high_24h")
        low_24h = agg.get("low_24h")
        volume_24h = agg.get("volume_24h")

        if first is None and last is None and high_24h is None and low_24h is None and volume_24h is None:
            continue

        prev_close = None
        if prev_sn is not None:
            prev_close = (
                MarketTrading24Hour.objects.filter(session_number=prev_sn, symbol=symbol)
                .values_list("close_24h", flat=True)
                .first()
            )

        range_diff = None
        range_pct = None
        if high_24h is not None and low_24h is not None:
            try:
                range_diff = high_24h - low_24h
            except Exception:
                range_diff = None
            try:
                if low_24h not in (None, 0):
                    range_pct = ((range_diff / low_24h) * Decimal("100")) if range_diff is not None else None
            except Exception:
                range_pct = None

        open_prev_diff = None
        open_prev_pct = None
        if first is not None and prev_close not in (None, 0):
            try:
                open_prev_diff = first - prev_close
            except Exception:
                open_prev_diff = None
            try:
                open_prev_pct = ((open_prev_diff / prev_close) * Decimal("100")) if open_prev_diff is not None else None
            except Exception:
                open_prev_pct = None

        obj, _created = MarketTrading24Hour.objects.get_or_create(
            session_number=session_number,
            symbol=symbol,
            defaults={
                "session_date": session_date,
            },
        )

        obj.session_date = session_date
        obj.prev_close_24h = prev_close
        obj.open_price_24h = first
        obj.close_24h = last
        obj.high_24h = high_24h
        obj.low_24h = low_24h
        obj.volume_24h = int(volume_24h or 0)
        obj.range_diff_24h = range_diff
        obj.range_pct_24h = range_pct
        obj.open_prev_diff_24h = open_prev_diff
        obj.open_prev_pct_24h = open_prev_pct
        obj.finalized = bool(obj.finalized)
        obj.save(
            update_fields=[
                "session_date",
                "prev_close_24h",
                "open_price_24h",
                "open_prev_diff_24h",
                "open_prev_pct_24h",
                "low_24h",
                "high_24h",
                "range_diff_24h",
                "range_pct_24h",
                "close_24h",
                "volume_24h",
                "finalized",
            ]
        )
        updated += 1

    return updated


def _pop_closed_bars(routing_key: str, batch_size: int = 500) -> Tuple[List[dict], List[str], int]:
    decoded, raw_items, queue_left = live_data_redis.checkout_closed_bars(routing_key, count=batch_size)
    return decoded, raw_items, queue_left


def _nack_closed_bars(routing_key: str, raw_items: List[str]) -> None:
    if not raw_items:
        return
    try:
        live_data_redis.return_closed_bars(routing_key, raw_items)
    except Exception:
        logger.exception("Failed to NACK closed bars for %s (may leave duplicates)", routing_key)


def _to_instrument_intraday_models(bars: List[dict]) -> List[InstrumentIntraday]:
    rows: List[InstrumentIntraday] = []

    for b in bars:
        try:
            raw_ts = b.get("t")
            if raw_ts is None:
                continue

            ts = datetime.fromtimestamp(int(raw_ts), tz=dt_timezone.utc)

            symbol = (b.get("symbol") or b.get("future") or "").strip()
            if not symbol:
                continue
            symbol = symbol.upper()

            bid = b.get("bid")
            ask = b.get("ask")
            spread = b.get("spread")

            def _to_decimal(v):
                if v is None:
                    return None
                try:
                    return Decimal(str(v))
                except Exception:
                    return None

            bid = _to_decimal(bid)
            ask = _to_decimal(ask)
            spread = _to_decimal(spread)

            if spread is None and bid is not None and ask is not None:
                try:
                    spread = _to_decimal(ask - bid)
                except Exception:
                    spread = None

            rows.append(
                InstrumentIntraday(
                    timestamp_minute=ts,
                    symbol=symbol,
                    open_1m=b.get("o"),
                    high_1m=b.get("h"),
                    low_1m=b.get("l"),
                    close_1m=b.get("c"),
                    volume_1m=int(b.get("v") or 0),
                    bid_last=bid,
                    ask_last=ask,
                    spread_last=spread,
                )
            )
        except Exception:
            logger.exception("Failed to convert instrument bar payload: %s", b)

    return rows


def flush_closed_bars(routing_key: str, batch_size: int = 500, max_batches: int = 20) -> int:
    total_inserted = 0
    prefix = str(routing_key)

    session_number = _parse_session_number(prefix)

    recovered = live_data_redis.requeue_processing_closed_bars(prefix)
    if recovered:
        logger.warning("Recovered %s bars from processing queue for %s", recovered, prefix)

    for _ in range(max_batches):
        bars, raw_items, queue_left = _pop_closed_bars(prefix, batch_size=batch_size)
        if not raw_items:
            break

        if not bars:
            live_data_redis.acknowledge_closed_bars(prefix, raw_items)
            logger.warning(
                "Decoded 0/%s bars for %s; ACKing raw batch to avoid stuck queue",
                len(raw_items),
                prefix,
            )
            if queue_left == 0:
                break
            continue

        instr_rows = _to_instrument_intraday_models(bars)
        if not instr_rows:
            live_data_redis.acknowledge_closed_bars(prefix, raw_items)
            logger.info(
                "minute close flush: route=%s decoded=%s rows=0 queue_left=%s",
                prefix,
                len(bars),
                queue_left,
            )
            if queue_left == 0:
                break
            continue

        try:
            with transaction.atomic():
                InstrumentIntraday.objects.bulk_create(instr_rows, ignore_conflicts=True)

                if session_number is not None:
                    symbols = _iter_unique_symbols(instr_rows)
                    try:
                        _recompute_market_trading_24h_for_symbols(session_number, symbols)
                    except Exception:
                        logger.exception("Failed to update MarketTrading24Hour for session_number=%s", session_number)

            try:
                latest_ts: Optional[datetime] = max(
                    [*(r.timestamp_minute for r in instr_rows if r.timestamp_minute)],
                    default=None,
                )
                if latest_ts:
                    cache_key = f"thor:last_bar_ts:{prefix}"
                    live_data_redis.client.set(cache_key, latest_ts.isoformat(), ex=3600)
            except Exception:
                logger.debug("Failed to cache last_bar_ts for %s", prefix, exc_info=True)

            total_inserted += len(instr_rows)
            live_data_redis.acknowledge_closed_bars(prefix, raw_items)

            logger.info(
                "minute close flush: route=%s decoded=%s instrument_inserted=%s queue_left=%s",
                prefix,
                len(bars),
                len(instr_rows),
                queue_left,
            )

        except Exception:
            logger.exception(
                "Failed bulk insert of %s bars for %s; NACKing batch",
                len(instr_rows),
                prefix,
            )
            _nack_closed_bars(prefix, raw_items)
            break

        if queue_left == 0:
            break

    return total_inserted
