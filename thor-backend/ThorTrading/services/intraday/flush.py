from __future__ import annotations
import logging
from datetime import datetime, timezone as dt_timezone
from typing import List, Tuple

from django.db import transaction
from LiveData.shared.redis_client import live_data_redis
from ThorTrading.models.Market24h import MarketTrading24Hour
from ThorTrading.models.MarketIntraDay import MarketIntraday
from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.services.config.country_codes import normalize_country_code

logger = logging.getLogger(__name__)


def _pop_closed_bars(country: str, batch_size: int = 500) -> Tuple[List[dict], List[str], int]:
    decoded, raw_items, queue_left = live_data_redis.checkout_closed_bars(country, count=batch_size)
    return decoded, raw_items, queue_left


def _resolve_session_group(country: str) -> int | None:
    return (
        MarketSession.objects
        .filter(country=country)
        .exclude(capture_group__isnull=True)
        .order_by('-capture_group')
        .values_list('capture_group', flat=True)
        .first()
    )


def _to_intraday_models(country: str, bars: List[dict], session_group: int | None):
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
            symbol = b.get("symbol") or b.get("future")
            if not symbol:
                continue
            symbol = symbol.upper()

            # Use latest capture_group when available; fall back to session_date to avoid dropping data
            sg = session_group
            if sg is None:
                if not warned_fallback:
                    warned_fallback = True
                    logger.warning(
                        "No capture_group found for %s; deferring bar flush until capture_group exists",
                        country,
                    )
                return []

            cache_key = (sg, symbol)
            twentyfour = twentyfour_cache.get(cache_key)
            if twentyfour is None:
                twentyfour, _ = MarketTrading24Hour.objects.get_or_create(
                    session_group=sg,
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


def flush_closed_bars(country: str, batch_size: int = 500, max_batches: int = 20) -> int:
    total_inserted = 0
    norm_country = normalize_country_code(country) or country
    session_group = _resolve_session_group(norm_country)

    recovered = live_data_redis.requeue_processing_closed_bars(norm_country)
    if recovered:
        logger.warning("Recovered %s bars from processing queue for %s", recovered, norm_country)

    for _ in range(max_batches):
        bars, raw_items, queue_left = _pop_closed_bars(norm_country, batch_size=batch_size)
        if not raw_items:
            break

        rows = _to_intraday_models(norm_country, bars, session_group=session_group)
        if session_group is None:
            # No capture_group yet: return bars to queue and stop to avoid data loss with mixed keys
            live_data_redis.return_closed_bars(norm_country, raw_items)
            logger.warning("Skipped flush for %s: capture_group missing; returned %s bars to queue", norm_country, len(bars))
            break
        if rows:
            try:
                with transaction.atomic():
                    MarketIntraday.objects.bulk_create(rows, ignore_conflicts=True)
                total_inserted += len(rows)
                live_data_redis.acknowledge_closed_bars(norm_country, raw_items)
            except Exception:
                logger.exception("Failed bulk insert of %s bars for %s", len(rows), country)
                live_data_redis.return_closed_bars(norm_country, raw_items)
                break
        else:
            # Nothing to insert (e.g., decode issues); drop or requeue? acknowledge to avoid stuck queue.
            live_data_redis.acknowledge_closed_bars(norm_country, raw_items)

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
