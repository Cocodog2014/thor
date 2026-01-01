from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from typing import List, Tuple

from django.db import transaction
from django.db.models import Max, Min
from django.utils import timezone

from LiveData.shared.redis_client import live_data_redis
from ThorTrading.models.Instrument_Intraday import InstrumentIntraday
from ThorTrading.models.extremes import Rolling52WeekStats

logger = logging.getLogger(__name__)


LOOKBACK_DAYS = 365


def _pop_closed_bars(routing_key: str, batch_size: int = 500) -> Tuple[List[dict], List[str], int]:
    """Atomically checkout a batch from main queue -> processing queue."""

    decoded, raw_items, queue_left = live_data_redis.checkout_closed_bars(routing_key, count=batch_size)
    return decoded, raw_items, queue_left


def _nack_closed_bars(routing_key: str, raw_items: List[str]) -> None:
    """Proper "NACK": remove items from processing queue, then requeue to main queue."""

    if not raw_items:
        return

    try:
        live_data_redis.return_closed_bars(routing_key, raw_items)
    except Exception:
        logger.exception("Failed to NACK closed bars for %s (may leave duplicates)", routing_key)


def _to_instrument_intraday_models(bars: List[dict]) -> List[InstrumentIntraday]:
    """Convert decoded bar dicts -> InstrumentIntraday ORM objects (neutral truth)."""

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

            rows.append(
                InstrumentIntraday(
                    timestamp_minute=ts,
                    symbol=symbol,
                    open_1m=b.get("o"),
                    high_1m=b.get("h"),
                    low_1m=b.get("l"),
                    close_1m=b.get("c"),
                    volume_1m=int(b.get("v") or 0),
                    bid_last=None,
                    ask_last=None,
                    spread_last=None,
                )
            )
        except Exception:
            logger.exception("Failed to convert instrument bar payload: %s", b)

    return rows


def _update_52w_from_closed_bars(instr_rows: List[InstrumentIntraday]) -> None:
    """Incrementally maintain Rolling52WeekStats from freshly flushed InstrumentIntraday rows."""

    if not instr_rows:
        return

    today = timezone.localdate()
    window_start = timezone.now() - timedelta(days=LOOKBACK_DAYS)

    by_symbol: dict[str, dict[str, Decimal | None]] = {}
    for r in instr_rows:
        if not r.symbol:
            continue
        bucket = by_symbol.setdefault(r.symbol, {"hi": None, "lo": None})
        if r.high_1m is not None:
            bucket["hi"] = r.high_1m if bucket["hi"] is None else max(bucket["hi"], r.high_1m)
        if r.low_1m is not None:
            bucket["lo"] = r.low_1m if bucket["lo"] is None else min(bucket["lo"], r.low_1m)

    for sym, mm in by_symbol.items():
        stats = Rolling52WeekStats.objects.filter(symbol=sym).first()
        if not stats:
            continue

        minute_high = mm.get("hi")
        minute_low = mm.get("lo")

        changed = False

        if minute_high is not None and (stats.high_52w is None or minute_high > stats.high_52w):
            stats.high_52w = minute_high
            stats.high_52w_date = today
            changed = True

        if minute_low is not None and (stats.low_52w is None or minute_low < stats.low_52w):
            stats.low_52w = minute_low
            stats.low_52w_date = today
            changed = True

        if stats.high_52w_date and stats.high_52w_date < (today - timedelta(days=LOOKBACK_DAYS)):
            agg = InstrumentIntraday.objects.filter(symbol=sym, timestamp_minute__gte=window_start).aggregate(
                h=Max("high_1m")
            )
            if agg["h"] is not None:
                stats.high_52w = agg["h"]
                stats.high_52w_date = today
                changed = True

        if stats.low_52w_date and stats.low_52w_date < (today - timedelta(days=LOOKBACK_DAYS)):
            agg = InstrumentIntraday.objects.filter(symbol=sym, timestamp_minute__gte=window_start).aggregate(
                l=Min("low_1m")
            )
            if agg["l"] is not None:
                stats.low_52w = agg["l"]
                stats.low_52w_date = today
                changed = True

        if changed:
            stats.last_price_checked = None
            stats.save(
                update_fields=[
                    "high_52w",
                    "high_52w_date",
                    "low_52w",
                    "low_52w_date",
                    "last_price_checked",
                    "last_updated",
                ]
            )


def flush_closed_bars(routing_key: str, batch_size: int = 500, max_batches: int = 20) -> int:
    """Drain Redis closed-bar queue and bulk insert into InstrumentIntraday only."""

    total_inserted = 0
    prefix = str(routing_key)

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

            try:
                latest_ts = max(
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

            if instr_rows:
                try:
                    _update_52w_from_closed_bars(instr_rows)
                except Exception:
                    logger.exception("Failed to update 52w stats from closed bars")

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
