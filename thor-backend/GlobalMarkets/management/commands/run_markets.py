# GlobalMarkets/management/commands/run_markets.py

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from GlobalMarkets.models import Market
from GlobalMarkets.services import compute_market_status

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return timezone.now()


def _sleep_seconds_until(next_dt_utc: Optional[datetime], *, min_sleep: float, max_sleep: float, poll_seconds: float) -> float:
    """
    If we know the next transition time, sleep until then (clamped).
    Otherwise, fall back to poll_seconds (clamped).
    """
    if not next_dt_utc:
        return max(min_sleep, min(max_sleep, poll_seconds))

    now = _utcnow()
    delta = (next_dt_utc - now).total_seconds()
    if delta < 0:
        delta = 0.0
    return max(min_sleep, min(max_sleep, delta))


def _broadcast_status_change(market: Market, old_status: str, new_status: str, when_utc: datetime) -> None:
    """
    Transition-only broadcast hook.

    We intentionally import inside the function so this runner can start
    even before you finish building publisher.py. If publisher.py is missing,
    it will just no-op.
    """
    try:
        from GlobalMarkets.publisher import publish_market_status_change  # type: ignore
    except Exception:
        return

    try:
        publish_market_status_change(
            market=market,
            previous_status=old_status,
            new_status=new_status,
            effective_at_utc=when_utc,
        )
    except Exception:
        logger.debug("Broadcast failed for %s", getattr(market, "key", market.pk), exc_info=True)


class Command(BaseCommand):
    help = "Run GlobalMarkets status transition loop (DB write + broadcast only on status changes)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run one iteration then exit (useful for debugging).",
        )
        parser.add_argument(
            "--poll",
            type=float,
            default=30.0,
            help="Fallback poll seconds when next transition can't be determined (default: 30).",
        )
        parser.add_argument(
            "--min-sleep",
            type=float,
            default=1.0,
            help="Minimum sleep seconds (default: 1).",
        )
        parser.add_argument(
            "--max-sleep",
            type=float,
            default=60.0,
            help="Maximum sleep seconds (default: 60).",
        )
        parser.add_argument(
            "--no-broadcast",
            action="store_true",
            help="Disable broadcasting on status changes.",
        )

    def handle(self, *args, **options):
        once: bool = options["once"]
        poll_seconds: float = options["poll"]
        min_sleep: float = options["min_sleep"]
        max_sleep: float = options["max_sleep"]
        broadcast_enabled: bool = not options["no_broadcast"]

        logger.info(
            "GlobalMarkets runner started (once=%s poll=%ss min_sleep=%ss max_sleep=%ss broadcast=%s)",
            once,
            poll_seconds,
            min_sleep,
            max_sleep,
            broadcast_enabled,
        )

        while True:
            loop_started = _utcnow()

            # Fetch active markets once per loop
            markets = list(Market.objects.filter(is_active=True).order_by("sort_order", "name"))

            earliest_next: Optional[datetime] = None
            checked = 0
            changed = 0

            for market in markets:
                checked += 1
                try:
                    computed = compute_market_status(market, now_utc=loop_started)
                except Exception:
                    logger.debug("compute_market_status failed for %s", getattr(market, "key", market.pk), exc_info=True)
                    continue

                if not computed:
                    continue

                new_status = computed.status
                old_status = market.status

                # Only persist when it actually changes
                if new_status != old_status:
                    try:
                        # Use a transaction so signals + DB state are consistent
                        with transaction.atomic():
                            # market.mark_status() saves only on change
                            market.mark_status(new_status, when=loop_started)
                    except Exception:
                        logger.exception("Failed to persist status change for %s", getattr(market, "key", market.pk))
                    else:
                        changed += 1
                        logger.info("Market %s status %s -> %s", market.key, old_status, new_status)

                        if broadcast_enabled:
                            _broadcast_status_change(market, old_status, new_status, loop_started)

                # Track earliest next transition across markets
                nxt = computed.next_transition_utc
                if nxt and (earliest_next is None or nxt < earliest_next):
                    earliest_next = nxt

            logger.info(
                "GlobalMarkets loop complete checked=%s changed=%s next=%s",
                checked,
                changed,
                earliest_next.isoformat() if earliest_next else None,
            )

            if once:
                return

            sleep_s = _sleep_seconds_until(
                earliest_next,
                min_sleep=min_sleep,
                max_sleep=max_sleep,
                poll_seconds=poll_seconds,
            )

            # Guard: if we are sleeping until a known transition, add a tiny pad so we don't wake up early due to clock skew
            if earliest_next:
                sleep_s = min(max_sleep, max(min_sleep, sleep_s + 0.25))

            time.sleep(sleep_s)
