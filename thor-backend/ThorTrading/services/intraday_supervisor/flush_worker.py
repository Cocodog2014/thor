import logging
from datetime import datetime, timezone as dt_timezone
from typing import List, Tuple

from django.db import transaction
from django.utils import timezone
from LiveData.shared.redis_client import live_data_redis
from ThorTrading.models.Martket24h import FutureTrading24Hour
from ThorTrading.models.MarketIntraDay import MarketIntraday
from ThorTrading.models.MarketSession import MarketSession

logger = logging.getLogger(__name__)


def _pop_closed_bars(country: str, batch_size: int = 500) -> Tuple[List[dict], int]:
    bars, queue_left = live_data_redis.dequeue_closed_bars(country, count=batch_size)
    return bars, queue_left


def _resolve_session_group(country: str) -> str | None:
    return (
        MarketSession.objects
        .filter(country=country)
        .exclude(capture_group__isnull=True)
        .order_by('-capture_group')
        .values_list('capture_group', flat=True)
        .first()
    )


def _to_intraday_models(country: str, bars: List[dict], session_group: str | None):
    rows = []
    twentyfour_cache = {}
    warned_fallback = False

    for b in bars:
        try:
            raw_ts = b.get("t")
            if raw_ts is None:
                logger.warning("Skipping bar with no timestamp for %s: %s", country, b)
                continue

            ts = datetime.fromtimestamp(int(raw_ts), tz=dt_timezone.utc)
            if timezone.is_naive(ts):
                ts = timezone.make_aware(ts, timezone=dt_timezone.utc)
            future = b.get("symbol") or b.get("future")
            if not future:
                continue
            future = future.upper()

            # Use latest capture_group when available; fall back to session_date to avoid dropping data
            sg = session_group
            if sg is None:
                sg = f"date:{ts.date().isoformat()}"
                if not warned_fallback:
                    warned_fallback = True
                    logger.warning(
                        "No capture_group found for %s; using session_date fallback %s for intraday bars",
                        country,
                        sg,
                    )

            cache_key = (sg, future)
            twentyfour = twentyfour_cache.get(cache_key)
            if twentyfour is None:
                twentyfour, _ = FutureTrading24Hour.objects.get_or_create(
                    session_group=str(sg),
                    future=future,
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
                    future=future,
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


def flush_closed_bars(country: str, batch_size: int = 500, max_batches: int = 20) -> int:
    total_inserted = 0
    session_group = _resolve_session_group(country)

    for _ in range(max_batches):
        bars, queue_left = _pop_closed_bars(country, batch_size=batch_size)
        if not bars:
            break

        rows = _to_intraday_models(country, bars, session_group=session_group)
        if rows:
            try:
                with transaction.atomic():
                    MarketIntraday.objects.bulk_create(rows, ignore_conflicts=True)
                total_inserted += len(rows)
            except Exception:
                logger.exception("Failed bulk insert of %s bars for %s", len(rows), country)
                break

        logger.info(
            "minute close flush: flushed=%s bars country=%s inserted=%s queue_left=%s",
            len(bars),
            country,
            len(rows),
            queue_left,
        )

        if queue_left == 0:
            break

    return total_inserted
