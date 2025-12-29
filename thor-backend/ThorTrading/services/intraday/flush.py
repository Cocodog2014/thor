from __future__ import annotations

import logging
from decimal import Decimal
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import List, Tuple

from django.db import transaction
from django.db.models import Max, Min
from django.utils import timezone

from LiveData.shared.redis_client import live_data_redis
from ThorTrading.models.Market24h import MarketTrading24Hour
from ThorTrading.models.MarketIntraDay import MarketIntraday
from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.models.Instrument_Intraday import InstrumentIntraday
from ThorTrading.models.extremes import Rolling52WeekStats

logger = logging.getLogger(__name__)


LOOKBACK_DAYS = 365


def _pop_closed_bars(routing_key: str, batch_size: int = 500) -> Tuple[List[dict], List[str], int]:
    """
    Atomically checkout a batch from main queue -> processing queue.
    Returns: (decoded_bars, raw_items, queue_left)
    """
    decoded, raw_items, queue_left = live_data_redis.checkout_closed_bars(routing_key, count=batch_size)
    return decoded, raw_items, queue_left


def _resolve_session_group(routing_key: str, bars: List[dict]) -> int | None:
    """
    Resolve session_group (capture_group) from routing key or bar payload.
    Prefers session_number embedded in payload; falls back to latest DB capture by country.
    """
    if bars:
        first = bars[0]
        session_number = first.get("session_number")
        if session_number is None:
            session_key = first.get("session_key") or routing_key
            if session_key:
                key_str = str(session_key).lower()
                if key_str.startswith("session:"):
                    key_str = key_str.split(":", 1)[1]
                try:
                    session_number = int(key_str)
                except Exception:
                    session_number = None
        if session_number is not None:
            return int(session_number)

    # Fallback: most recent capture_group for the country in payload
    country = None
    if bars:
        country = bars[0].get("country")
    if not country:
        return None

    return (
        MarketSession.objects
        .filter(country=country)
        .exclude(capture_group__isnull=True)
        .order_by("-capture_group")
        .values_list("capture_group", flat=True)
        .first()
    )


def _nack_closed_bars(routing_key: str, raw_items: List[str]) -> None:
    """
    Proper "NACK": remove items from processing queue, then requeue to main queue.
    This avoids duplicates where items exist in both queues.
    """
    if not raw_items:
        return

    try:
        live_data_redis.return_closed_bars(routing_key, raw_items)
    except Exception:
        logger.exception("Failed to NACK closed bars for %s (may leave duplicates)", routing_key)


def _to_intraday_models(country: str, bars: List[dict], session_group: int) -> List[MarketIntraday]:
    """
    Convert decoded bar dicts -> MarketIntraday ORM objects.
    Requires session_group (strict mode).
    """
    rows: List[MarketIntraday] = []
    twentyfour_cache = {}

    if not country:
        logger.warning("Skipping intraday conversion: missing country in bar payload")
        return rows

    for b in bars:
        try:
            raw_ts = b.get("t")
            if raw_ts is None:
                logger.warning("Skipping bar with no timestamp for %s: %s", country, b)
                continue

            ts = datetime.fromtimestamp(int(raw_ts), tz=dt_timezone.utc)

            symbol = (b.get("symbol") or b.get("future") or "").strip()
            if not symbol:
                continue
            symbol = symbol.upper()

            cache_key = (session_group, symbol)
            twentyfour = twentyfour_cache.get(cache_key)
            if twentyfour is None:
                twentyfour, _ = MarketTrading24Hour.objects.get_or_create(
                    session_group=session_group,
                    symbol=symbol,
                    defaults={
                        "session_date": ts.date(),
                        "country": country,
                    },
                )
                twentyfour_cache[cache_key] = twentyfour

            rows.append(
                MarketIntraday(
                    timestamp_minute=ts,
                    country=country,
                    symbol=symbol,
                    twentyfour=twentyfour,
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
            logger.exception("Failed to convert bar payload for %s: %s", country, b)

    return rows


def _to_instrument_intraday_models(bars: List[dict]) -> List[InstrumentIntraday]:
    """
    Convert decoded bar dicts -> InstrumentIntraday ORM objects (neutral truth).
    No country, no session_group required.
    """
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
    """
    Incrementally maintain Rolling52WeekStats from freshly flushed InstrumentIntraday rows.
    - Update on new highs/lows within the batch.
    - Recompute a side if the stored extreme is older than LOOKBACK_DAYS.
    """
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
            continue  # Require seed to avoid creating incomplete rows

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
            agg = (
                InstrumentIntraday.objects
                .filter(symbol=sym, timestamp_minute__gte=window_start)
                .aggregate(h=Max("high_1m"))
            )
            if agg["h"] is not None:
                stats.high_52w = agg["h"]
                stats.high_52w_date = today
                changed = True

        if stats.low_52w_date and stats.low_52w_date < (today - timedelta(days=LOOKBACK_DAYS)):
            agg = (
                InstrumentIntraday.objects
                .filter(symbol=sym, timestamp_minute__gte=window_start)
                .aggregate(l=Min("low_1m"))
            )
            if agg["l"] is not None:
                stats.low_52w = agg["l"]
                stats.low_52w_date = today
                changed = True

        if changed:
            stats.last_price_checked = None
            stats.save(update_fields=[
                "high_52w",
                "high_52w_date",
                "low_52w",
                "low_52w_date",
                "last_price_checked",
                "last_updated",
            ])


def flush_closed_bars(routing_key: str, batch_size: int = 500, max_batches: int = 20) -> int:
    """
    Drain Redis closed-bar queue for a country and bulk insert into MarketIntraday.
    Strict for MarketIntraday; always-write InstrumentIntraday.

    If capture_group/session_group is missing, we defer MarketIntraday (projection) but
    still persist InstrumentIntraday (truth) so 52w stats and downstream readers stay current.

    Safety:
      - Requeues bars stuck in processing (crash recovery)
      - Uses processing queue with ACK/NACK semantics
    """
    total_inserted = 0
    prefix = str(routing_key)

    # 1) Crash recovery: move any stuck processing items back to main queue
    recovered = live_data_redis.requeue_processing_closed_bars(prefix)
    if recovered:
        logger.warning("Recovered %s bars from processing queue for %s", recovered, prefix)

    # 2) Resolve session_group (DB capture_group) for MarketIntraday
    session_group = None

    # 3) Drain in batches
    for _ in range(max_batches):
        bars, raw_items, queue_left = _pop_closed_bars(prefix, batch_size=batch_size)
        if not raw_items:
            break

        if not bars:
            # Nothing decoded -> ACK raw items to avoid a stuck processing queue
            live_data_redis.acknowledge_closed_bars(prefix, raw_items)
            logger.warning("Decoded 0/%s bars for %s; ACKing raw batch to avoid stuck queue", len(raw_items), prefix)
            if queue_left == 0:
                break
            continue

        if session_group is None:
            session_group = _resolve_session_group(prefix, bars)
        session_group_available = session_group is not None

        instr_rows = _to_instrument_intraday_models(bars)
        rows = _to_intraday_models(
            bars[0].get("country") if bars else None,
            bars,
            session_group=session_group,
        ) if session_group_available else []

        if not rows and not instr_rows:
            # If nothing to insert (e.g. missing symbols), ACK so we don't loop forever
            live_data_redis.acknowledge_closed_bars(prefix, raw_items)
            logger.info("minute close flush: route=%s decoded=%s rows=0 queue_left=%s", prefix, len(bars), queue_left)
            if queue_left == 0:
                break
            continue

        try:
            with transaction.atomic():
                if rows:
                    MarketIntraday.objects.bulk_create(rows, ignore_conflicts=True)
                if instr_rows:
                    InstrumentIntraday.objects.bulk_create(instr_rows, ignore_conflicts=True)

            # Cache the latest flushed bar timestamp in Redis to avoid per-second DB hits in lag checks
            try:
                latest_ts = max(
                    [
                        *(r.timestamp_minute for r in rows if r.timestamp_minute),
                        *(r.timestamp_minute for r in instr_rows if r.timestamp_minute),
                    ],
                    default=None,
                )
                if latest_ts:
                    cache_key = f"thor:last_bar_ts:{prefix}"
                    live_data_redis.client.set(cache_key, latest_ts.isoformat(), ex=3600)
            except Exception:
                logger.debug("Failed to cache last_bar_ts for %s", prefix, exc_info=True)

            total_inserted += len(rows)
            live_data_redis.acknowledge_closed_bars(prefix, raw_items)

            if instr_rows:
                try:
                    _update_52w_from_closed_bars(instr_rows)
                except Exception:
                    logger.exception("Failed to update 52w stats from closed bars")

            logger.info(
                "minute close flush: route=%s decoded=%s market_inserted=%s instrument_inserted=%s queue_left=%s",
                prefix,
                len(bars),
                len(rows),
                len(instr_rows),
                queue_left,
            )

        except Exception:
            logger.exception("Failed bulk insert of %s bars for %s; NACKing batch", len(rows), prefix)
            _nack_closed_bars(prefix, raw_items)
            break

        if queue_left == 0:
            break

    return total_inserted
