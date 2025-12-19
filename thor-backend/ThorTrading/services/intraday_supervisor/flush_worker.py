import json
import logging
from datetime import datetime
from typing import List, Tuple

from django.db import transaction
from django.utils import timezone

from LiveData.shared.redis_client import live_data_redis
from ThorTrading.models.MarketIntraDay import MarketIntraday
from ThorTrading.services.country_codes import normalize_country_code

logger = logging.getLogger(__name__)


def _pop_closed_bars(country: str, batch_size: int = 500) -> Tuple[List[dict], int]:
    bars = live_data_redis.dequeue_closed_bars(country, count=batch_size)
    queue_left = 0
    return bars, queue_left


def _to_intraday_models(country: str, bars: List[dict]):
    rows = []
    for b in bars:
        try:
            ts = datetime.fromtimestamp(int(b["t"]), tz=timezone.utc)
            future = b.get("symbol") or b.get("future")
            if not future:
                continue
            rows.append(
                MarketIntraday(
                    timestamp_minute=ts,
                    country=normalize_country_code(country) or country,
                    future=future.upper(),
                    twentyfour=None,  # defer linking unless provided elsewhere
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


def flush_closed_bars(country: str, batch_size: int = 500) -> int:
    bars, queue_left = _pop_closed_bars(country, batch_size=batch_size)
    if not bars:
        return 0

    rows = _to_intraday_models(country, bars)
    if not rows:
        return 0

    try:
        with transaction.atomic():
            MarketIntraday.objects.bulk_create(rows, ignore_conflicts=True)
    except Exception:
        logger.exception("Failed bulk insert of %s bars for %s", len(rows), country)
        return 0

    inserted = len(rows)
    logger.info(
        "minute close flush: flushed=%s bars country=%s inserted=%s queue_left=%s",
        len(bars),
        country,
        inserted,
        queue_left,
    )
    return inserted
