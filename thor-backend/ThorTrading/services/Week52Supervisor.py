"""
Week 52 (52-Week) Extremes Monitor

Continuously reads latest quotes from Redis and updates
`ThorTrading.models.Rolling52WeekStats` when new highs/lows occur.

Note: This file was renamed from a previous misspelling to fix a typo.
"""

from __future__ import annotations

import logging
import threading
import time
from decimal import Decimal
from typing import Dict, List, Callable
import os

from django.conf import settings

logger = logging.getLogger(__name__)


class _ExtremesMonitor:
    """Background thread that updates 52-week extremes from Redis quotes."""

    SYMBOLS: List[str] = ['YM', 'ES', 'NQ', 'RTY', 'CL', 'SI', 'HG', 'GC', 'VX', 'DX', 'ZB']

    SYMBOL_MAP: Dict[str, str] = {
        'RTY': 'RT',
        'ZB': '30YRBOND',
    }

    def __init__(self, interval_seconds: float = 1.0):
        self._interval = max(0.25, float(interval_seconds))
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._running = False
        self._tick = 0
        self._last_update_symbol: str | None = None
        self._last_update_time: str | None = None

    def start(self):
        import os
        scheduler_mode = os.getenv("THOR_SCHEDULER_MODE", "heartbeat").lower()
        if scheduler_mode == "heartbeat":
            logger.info("Heartbeat scheduler active; skipping legacy 52w extremes monitor")
            return
        with self._lock:
            if self._running:
                logger.debug("52w monitor already running; skipping start")
                return
            self._running = True
            t = threading.Thread(target=self._run, name="Week52ExtremesMonitor", daemon=True)
            self._thread = t
            t.start()
            logger.info("📈 52-Week Extremes monitor started (interval=%.2fs)", self._interval)

    def stop(self):
        with self._lock:
            self._running = False
        logger.info("🛑 52-Week Extremes monitor stop requested")

    def _run(self):
        from LiveData.shared.redis_client import live_data_redis
        from ThorTrading.models.extremes import Rolling52WeekStats
        from django.utils import timezone

        while True:
            with self._lock:
                if not self._running:
                    break

            try:
                for sym in self.SYMBOLS:
                    redis_sym = self.SYMBOL_MAP.get(sym, sym)
                    quote = live_data_redis.get_latest_quote(redis_sym)
                    if not quote or not quote.get('last'):
                        continue

                    try:
                        last_price = Decimal(str(quote['last']))
                    except Exception:
                        continue

                    stats, created = Rolling52WeekStats.objects.get_or_create(
                        symbol=sym,
                        defaults={
                            'high_52w': last_price,
                            'high_52w_date': timezone.now().date(),
                            'low_52w': last_price,
                            'low_52w_date': timezone.now().date(),
                        },
                    )

                    if created:
                        logger.debug("[52w] Created initial stats for %s at %s", sym, last_price)
                        continue

                    if stats.update_from_price(last_price):
                        logger.info(
                            "🎯 [52w] %s updated: H=%s (%s) L=%s (%s)",
                            sym,
                            stats.high_52w,
                            stats.high_52w_date,
                            stats.low_52w,
                            stats.low_52w_date,
                        )
                        self._last_update_symbol = sym
                        self._last_update_time = timezone.now().isoformat(timespec='seconds')
            except Exception:
                logger.exception("[52w] Monitor iteration failed")

            time.sleep(self._interval)

            self._tick += 1
            if self._tick % 60 == 0:
                logger.info(
                    "💓 [52w heartbeat] tick=%d interval=%.2fs last_update=%s@%s",
                    self._tick,
                    self._interval,
                    self._last_update_symbol or '-',
                    self._last_update_time or 'none'
                )


__monitor_instance: _ExtremesMonitor | None = None


def _get_interval() -> float:
    setting = getattr(settings, 'FUTURETRADING_52W_MONITOR_INTERVAL', None)
    if setting is not None:
        return float(setting)
    env = os.getenv('FUTURETRADING_52W_MONITOR_INTERVAL')
    return float(env) if env else 1.0


def get_52w_monitor() -> _ExtremesMonitor:
    global __monitor_instance
    if __monitor_instance is None:
        __monitor_instance = _ExtremesMonitor(interval_seconds=_get_interval())
    return __monitor_instance


def _is_enabled() -> bool:
    setting = getattr(settings, 'FUTURETRADING_ENABLE_52W_MONITOR', None)
    if setting is not None:
        return bool(setting)
    env = os.getenv('FUTURETRADING_ENABLE_52W_MONITOR')
    if env is None:
        return True
    return env.strip().lower() not in {'0', 'false', 'no', 'off'}


def start_52w_monitor() -> None:
    for t in threading.enumerate():
        if t.name == "Week52ExtremesMonitor":
            logger.debug("Duplicate 52w monitor thread detected; skipping new start")
            return
    logger.info("🔍 Attempting to start 52-Week Extremes monitor...")
    if not _is_enabled():
        logger.warning("⚠️ 52-Week Extremes monitor disabled by settings/env")
        return
    logger.info("✅ Monitor enabled; starting background thread")
    mon = get_52w_monitor()
    mon.start()


def stop_52w_monitor() -> None:
    mon = get_52w_monitor()
    mon.stop()


_supervisor_thread: threading.Thread | None = None
_supervisor_running = False
_supervisor_lock = threading.RLock()


def _get_supervisor_interval() -> float:
    setting = getattr(settings, 'FUTURETRADING_52W_SUPERVISOR_INTERVAL', None)
    if setting is not None:
        return float(setting)
    env = os.getenv('FUTURETRADING_52W_SUPERVISOR_INTERVAL')
    return float(env) if env else 60.0


def _any_control_markets_open() -> bool:
    try:
        from GlobalMarkets.models.market import Market
        if Market.objects.filter(is_control_market=True, is_active=True, status='OPEN').exists():
            return True
        for m in Market.objects.filter(is_control_market=True, is_active=True):
            try:
                if m.is_market_open_now():
                    return True
            except Exception:
                continue
    except Exception:
        logger.exception("[52w supervisor] Failed checking market statuses")
    return False


def _supervisor_loop(interval: float, is_market_open_fn: Callable[[], bool]):
    global _supervisor_running
    logger.info("🛰️ 52w supervisor started (interval=%.1fs)", interval)
    _evaluate_and_toggle(is_market_open_fn)
    while True:
        with _supervisor_lock:
            if not _supervisor_running:
                break
        try:
            _evaluate_and_toggle(is_market_open_fn)
        except Exception:
            logger.exception("[52w supervisor] Evaluation failed")
        time.sleep(interval)
    logger.info("🛑 52w supervisor stopped")


def _evaluate_and_toggle(is_market_open_fn: Callable[[], bool]):
    open_any = is_market_open_fn()
    mon = get_52w_monitor()
    if not _is_enabled():
        if mon._running:
            mon.stop()
        logger.debug("[52w supervisor] monitor disabled by config; forced stopped")
        return
    if open_any:
        mon.start()
    else:
        mon.stop()
    logger.debug("[52w supervisor] markets_open=%s monitor_running=%s", open_any, mon._running)


def start_52w_monitor_supervisor() -> None:
    global _supervisor_thread, _supervisor_running
    with _supervisor_lock:
        if _supervisor_running:
            logger.debug("[52w supervisor] Already running; skip start")
            return
        _supervisor_running = True
        interval = _get_supervisor_interval()
        t = threading.Thread(
            target=_supervisor_loop,
            name="Week52ExtremesSupervisor",
            daemon=True,
            args=(interval, _any_control_markets_open),
        )
        _supervisor_thread = t
        t.start()


def stop_52w_monitor_supervisor() -> None:
    global _supervisor_running
    with _supervisor_lock:
        _supervisor_running = False
    logger.info("🛑 52w supervisor stop requested")

