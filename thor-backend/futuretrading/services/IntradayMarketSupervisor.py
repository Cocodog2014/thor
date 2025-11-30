# FutureTrading/services/IntradayMarketSupervisor.py

"""
Intraday Market Supervisor
=========================

Purpose
-------
Continuously process live quotes for each OPEN market and update:

1) Intraday extremes (true session high/low) used by dashboards
    - MarketHighMetric.update_from_quotes
    - MarketLowMetric.update_from_quotes

2) Rolling 24-hour session stats (JP→US window)
    - FutureTrading24Hour (low_24h, high_24h, range_diff_24h, range_pct_24h, volume_24h)
    - Finalized later at US close by MarketCloseMetric

3) 1-minute OHLCV bars per instrument
    - MarketIntraday (open_1m, high_1m, low_1m, close_1m, volume_1m)
    - Bars are persisted once per minute per symbol and are linked to the current 24h row

4) Session cumulative volume
    - MarketSession.session_volume accumulates while the market is OPEN

Lifecycle
---------
- The Global MarketMonitor calls on_market_open(market) → starts a worker thread for that country.
- The worker loop fetches enriched quotes, updates metrics and tables, then sleeps for `interval_seconds` (default 10s).
- On market close: on_market_close(market) stops the worker and runs close/range metrics once.

Performance & Write Strategy
----------------------------
- Reads many ticks per second from Redis (via get_enriched_quotes_with_composite).
- Writes sparingly:
  * 24h row only when a new extreme appears or on volume increments.
  * 1-minute bars are created per minute bucket (get_or_create), not per tick.
  * Session volume increments per loop using the latest MarketSession.

Key Concepts
------------
- "24h" fields reflect the broker-provided rolling 24-hour window (not the intraday session).
- "market_*_open" fields reflect intraday session extremes (initialized at session open using last_price).
- capture_group ties MarketSession and 24h records together; latest capture_group per country is used.

Notes for Developers
--------------------
- If you need true per-second persistence, don’t store ticks in Postgres; use Redis for the stream and aggregate to minute bars.
- If no MarketSession exists yet for the country (no open capture), 24h/intraday updates are skipped until capture occurs.
- Timezone: Use timezone-aware datetimes (timezone.now()); minute_bucket is computed with seconds/micros zeroed.
"""

import logging
import threading
import time
import os
import json
from django.utils import timezone
from LiveData.shared.redis_client import live_data_redis
from FutureTrading.constants import FUTURES_SYMBOLS
from FutureTrading.services.vwap import vwap_service
from django.db import transaction
from django.utils import timezone
from FutureTrading.models.Martket24h import FutureTrading24Hour
from FutureTrading.models.MarketIntraDay import MarketIntraday
from FutureTrading.models.MarketSession import MarketSession

from FutureTrading.services.quotes import get_enriched_quotes_with_composite
from FutureTrading.services.market_metrics import (
    MarketHighMetric,
    MarketLowMetric,
    MarketCloseMetric,
    MarketRangeMetric,
)

logger = logging.getLogger(__name__)


class IntradayMarketSupervisor:
    """
    Manages background metric updates for each OPEN market (country).

    Features:
        - Each OPEN market gets its own worker thread.
        - High/Low (intraday session) metrics update on a repeating schedule.
        - Rolling 24h extremes & volume are updated as quotes evolve.
        - 1-minute bars are persisted per symbol per minute.
        - When the market closes, the worker stops and close/range metrics run once.
    """

    def __init__(self, interval_seconds: int = 10):
        # How often to refresh highs/lows while market is open
        self.interval_seconds = interval_seconds

        # Allow migrations/maintenance to disable the background workers entirely
        self.disabled = os.getenv("INTRADAY_SUPERVISOR_DISABLED", "").lower() in {"1", "true", "yes"}
        if self.disabled:
            logger.warning("IntradayMarketSupervisor disabled via INTRADAY_SUPERVISOR_DISABLED")

        # Map: market.id -> (thread, stop_event)
        self._workers = {}
        self._lock = threading.RLock()

    # --------------------------------------------------------------------
    # PUBLIC API - Called by MarketMonitor
    # --------------------------------------------------------------------

    def on_market_open(self, market):
        """Start intraday metric updates for this market (if not already running)."""
        if self.disabled:
            logger.info("Intraday metrics disabled; skipping worker start for %s", market.country)
            return
        with self._lock:
            if market.id in self._workers:
                logger.info("Intraday worker already active for %s", market.country)
                return

            stop_event = threading.Event()
            thread = threading.Thread(
                target=self._worker_loop,
                name=f"Intraday-{market.country}",
                args=(market, stop_event),
                daemon=True,
            )

            # Register worker for this market
            self._workers[market.id] = (thread, stop_event)
            thread.start()

            logger.info("Intraday metrics worker STARTED for %s", market.country)

    def on_market_close(self, market):
        """Stop intraday updates and finalize market_close & market_range metrics."""
        if self.disabled:
            logger.info("Intraday metrics disabled; skipping close handling for %s", market.country)
            return
        with self._lock:
            worker = self._workers.pop(market.id, None)
            if worker:
                thread, stop_event = worker
                stop_event.set()
                thread.join(timeout=5)
                logger.info("Intraday metrics worker STOPPED for %s", market.country)

        # Now run close + range metrics once
        try:
            enriched, composite = get_enriched_quotes_with_composite()
        except Exception:
            logger.exception(
                "Failed to fetch quotes for close metrics (%s)", market.country
            )
            return

        try:
            MarketCloseMetric.update_for_country_on_close(market.country, enriched)
        except Exception:
            logger.exception("MarketCloseMetric failed for %s", market.country)

        try:
            MarketRangeMetric.update_for_country_on_close(market.country)
        except Exception:
            logger.exception("MarketRangeMetric failed for %s", market.country)

    # --------------------------------------------------------------------
    # INTERNAL WORKER LOOP
    # --------------------------------------------------------------------

    def _worker_loop(self, market, stop_event: threading.Event):
        """
        Loop that runs while market is OPEN.

        Processing per iteration:
        - Fetch enriched quotes for tracked instruments (includes broker 24h highs/lows).
        - Update intraday session highs/lows.
        - Upsert the country’s 24h row per instrument (extremes, range, volume).
        - Create/get the current minute’s OHLCV bar per instrument.
        - Accumulate session volume on the latest MarketSession.

        The loop sleeps for `self.interval_seconds` to control write cadence.
        """
        if self.disabled:
            logger.info("Intraday worker requested for %s but supervisor is disabled", market.country)
            return
        country = market.country
        logger.info("Intraday worker loop started for %s", country)

        while not stop_event.is_set():
            try:
                enriched, composite = get_enriched_quotes_with_composite()

                # Continuous intraday updates
                MarketHighMetric.update_from_quotes(country, enriched)
                MarketLowMetric.update_from_quotes(country, enriched)

                # --- New: Feed 24h session and 1m intraday bars ---
                try:
                    updated_counts = self._update_24h_and_intraday(country, enriched)
                    logger.info(
                        "Intraday loop %s → 24h-updated=%s, intraday-bars=%s, session-volume-updates=%s",
                        country,
                        updated_counts.get('twentyfour_updates', 0),
                        updated_counts.get('intraday_bars', 0),
                        updated_counts.get('session_volume_updates', 0),
                    )
                except Exception as feed_err:
                    logger.debug("24h/intraday feed failed for %s: %s", country, feed_err)

                # Rolling VWAP precomputation
                window_minutes = int(os.getenv('ROLLING_VWAP_WINDOW_MINUTES', '30'))
                now_dt = timezone.now().replace(second=0, microsecond=0)
                vwap_payload = {}
                for sym in FUTURES_SYMBOLS:
                    try:
                        val = vwap_service.calculate_rolling_vwap(sym, window_minutes, now_dt=now_dt)
                        vwap_payload[sym] = str(val) if val is not None else None
                    except Exception as vw_err:
                        logger.debug("Rolling VWAP calc failed for %s: %s", sym, vw_err)
                        vwap_payload[sym] = None
                live_data_redis.set_json(
                    f"rolling_vwap:{window_minutes}",
                    {
                        'window_minutes': window_minutes,
                        'as_of': now_dt.isoformat(),
                        'values': vwap_payload,
                    },
                    ex=120,
                )

            except Exception:
                logger.exception("Intraday metrics update failed for %s", country)

            stop_event.wait(self.interval_seconds)

        logger.info("Intraday worker loop EXITING for %s", country)

    @transaction.atomic
    def _update_24h_and_intraday(self, country: str, enriched_rows):
        """Update rolling 24h stats and append 1-minute bars.

        - 24h row: Upsert per (capture_group, future) using latest capture_group for `country`.
            * Initialize extremes if missing, then roll forward when new highs/lows appear.
            * Recompute range_diff_24h and range_pct_24h when either extreme changes.
            * Increment volume_24h per pass using the current tick volume.

        - Intraday bar: Create per (minute, future, country) linked to 24h row.
            * This ensures exactly one OHLCV row per minute per instrument.
            * Volume_1m holds the accumulated tick volume for the minute.

        - Session volume: Accumulate on the latest MarketSession for this country/future.
            * Provides per-market session volume for analytics.
        """
        if not enriched_rows:
            return {'twentyfour_updates': 0, 'intraday_bars': 0, 'session_volume_updates': 0}

        latest_group = (
            MarketSession.objects
            .filter(country=country)
            .exclude(capture_group__isnull=True)
            .order_by('-capture_group')
            .values_list('capture_group', flat=True)
            .first()
        )
        if latest_group is None:
            # No session yet for this country; skip until a capture exists.
            # MarketOpenCapture will set up MarketSession and capture_group.
            return {'twentyfour_updates': 0, 'intraday_bars': 0, 'session_volume_updates': 0}

        # Minute bucket in UTC
        now_dt = timezone.now()
        minute_bucket = now_dt.replace(second=0, microsecond=0)

        counts = {'twentyfour_updates': 0, 'intraday_bars': 0, 'session_volume_updates': 0}
        for row in enriched_rows:
            sym = row.get('instrument', {}).get('symbol')
            if not sym:
                continue
            future = sym.lstrip('/').upper()

            last = row.get('last')
            high_price = row.get('high_price')
            low_price = row.get('low_price')
            open_price = row.get('open_price')
            prev_close = row.get('previous_close') or row.get('close_price')
            vol = int(row.get('volume') or 0)

            # Upsert 24h session row (linked by capture_group)
            twentyfour, _ = FutureTrading24Hour.objects.get_or_create(
                session_group=str(latest_group),
                future=future,
                defaults={
                    'session_date': now_dt.date(),
                    'country': country,
                    'open_price_24h': self._safe_decimal(open_price),
                    'prev_close_24h': self._safe_decimal(prev_close),
                }
            )
            updated = False
            # Initialize extremes if missing
            if twentyfour.low_24h is None and low_price is not None:
                twentyfour.low_24h = self._safe_decimal(low_price)
                updated = True
            if twentyfour.high_24h is None and high_price is not None:
                twentyfour.high_24h = self._safe_decimal(high_price)
                updated = True
            # Roll extremes forward
            if high_price is not None:
                hp = self._safe_decimal(high_price)
                if hp is not None and (twentyfour.high_24h is None or hp > twentyfour.high_24h):
                    twentyfour.high_24h = hp
                    updated = True
            if low_price is not None:
                lp = self._safe_decimal(low_price)
                if lp is not None and (twentyfour.low_24h is None or lp < twentyfour.low_24h):
                    twentyfour.low_24h = lp
                    updated = True
            # Recompute range
            if twentyfour.high_24h is not None and twentyfour.low_24h is not None and twentyfour.open_price_24h not in (None, 0):
                try:
                    rng = twentyfour.high_24h - twentyfour.low_24h
                    pct = (rng / twentyfour.open_price_24h) * Decimal('100')
                    twentyfour.range_diff_24h = rng
                    twentyfour.range_pct_24h = pct
                    updated = True
                except Exception:
                    pass
            if updated:
                twentyfour.save(update_fields=['low_24h', 'high_24h', 'range_diff_24h', 'range_pct_24h'])
                counts['twentyfour_updates'] += 1

            # Increment 24h volume
            try:
                current_vol = twentyfour.volume_24h or 0
                twentyfour.volume_24h = current_vol + vol
                twentyfour.save(update_fields=['volume_24h'])
                counts['twentyfour_updates'] += 1
            except Exception:
                pass

            # Append/create 1-minute bar (one per minute per instrument)
            obj, created = MarketIntraday.objects.get_or_create(
                timestamp_minute=minute_bucket,
                country=country,
                future=future,
                defaults={
                    'market_code': country,
                    'twentyfour': twentyfour,
                    'open_1m': self._safe_decimal(last),
                    'high_1m': self._safe_decimal(last),
                    'low_1m': self._safe_decimal(last),
                    'close_1m': self._safe_decimal(last),
                    'volume_1m': vol,
                }
            )
            if created:
                counts['intraday_bars'] += 1

            # Increment session volume on latest MarketSession row
            session = (
                MarketSession.objects
                .filter(country=country, future=future)
                .order_by('-session_number')
                .first()
            )
            if session:
                try:
                    sv = session.session_volume or 0
                    session.session_volume = sv + vol
                    session.save(update_fields=['session_volume'])
                    counts['session_volume_updates'] += 1
                except Exception:
                    pass

        return counts

    @staticmethod
    def _safe_decimal(val):
        from decimal import Decimal as D
        if val in (None, '', ' '):
            return None
        try:
            return D(str(val))
        except Exception:
            return None


# Global singleton used by MarketMonitor
intraday_market_supervisor = IntradayMarketSupervisor()
