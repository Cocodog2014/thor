"""Background VWAP minute capture service.

Translates the `capture_vwap_minutes` management command into a reusable
service so GlobalMarkets can orchestrate when VWAP source data should be
recorded. The service stores up to one `VwapMinute` row per symbol per
minute, mirroring the legacy command implementation.
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict

from django.utils import timezone

from LiveData.shared.redis_client import live_data_redis
from ThorTrading.constants import FUTURES_SYMBOLS, REDIS_SYMBOL_MAP
from ThorTrading.models.vwap import VwapMinute

logger = logging.getLogger(__name__)


def _floor_to_minute(dt: datetime) -> datetime:
    return dt.replace(second=0, microsecond=0)


def _dec(val):
    if val in (None, "", " "):
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


def _int(val):
    if val in (None, "", " "):
        return None
    try:
        return int(val)
    except Exception:
        try:
            return int(float(val))
        except Exception:
            return None


@dataclass
class _CaptureStats:
    samples: int = 0
    rows_created: int = 0


def _capture_interval() -> int:
    env = os.getenv("FUTURETRADING_VWAP_CAPTURE_INTERVAL")
    if env:
        try:
            return max(5, int(float(env)))
        except Exception:
            logger.warning("Invalid FUTURETRADING_VWAP_CAPTURE_INTERVAL=%s", env)
    return 60


class VWAPMinuteCaptureService:
    """Threaded service that mirrors the capture_vwap_minutes command."""

    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = max(5, int(interval_seconds))
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_minute_per_symbol: Dict[str, datetime] = {}
        self._stats = _CaptureStats()

    def start(self) -> bool:
        # Skip if heartbeat scheduler is running (new unified approach)
        import os
        scheduler_mode = os.getenv("THOR_SCHEDULER_MODE", "heartbeat").lower()
        if scheduler_mode == "heartbeat":
            logger.info("Heartbeat scheduler active; skipping legacy VWAP capture thread")
            return False
        with self._lock:
            if self._thread and self._thread.is_alive():
                logger.info("VWAP capture already running; skip start")
                return False
            self._stop_event.clear()
            thread = threading.Thread(
                target=self._run,
                name="VwapMinuteCapture",
                daemon=True,
            )
            self._thread = thread
            thread.start()
        logger.info(
            "VWAP minute capture started (interval=%ss)",
            self.interval_seconds,
        )
        return True

    def stop(self, wait: bool = False) -> bool:
        with self._lock:
            thread = self._thread
            if not thread:
                return False
            self._stop_event.set()
        if wait:
            thread.join(timeout=10)
        if not thread.is_alive():
            with self._lock:
                self._thread = None
        logger.info("VWAP minute capture stop requested")
        return True

    def _run(self):
        try:
            self._loop()
        except Exception:
            logger.exception("VWAP minute capture loop crashed")
        finally:
            with self._lock:
                self._thread = None
                self._stop_event.clear()

    def _loop(self):
        while not self._stop_event.is_set():
            self._stats.samples += 1
            now = timezone.now()
            current_minute = _floor_to_minute(now)
            for sym in FUTURES_SYMBOLS:
                redis_key = REDIS_SYMBOL_MAP.get(sym, sym)
                quote = live_data_redis.get_latest_quote(redis_key)
                if not quote:
                    continue
                # Skip duplicates for this minute
                if self._last_minute_per_symbol.get(sym) == current_minute:
                    continue
                try:
                    defaults = {
                        "last_price": _dec(quote.get("last")),
                        "cumulative_volume": _int(quote.get("volume")),
                    }
                    _, created = VwapMinute.objects.update_or_create(
                        symbol=sym,
                        timestamp_minute=current_minute,
                        defaults=defaults,
                    )
                    self._last_minute_per_symbol[sym] = current_minute
                    if created:
                        self._stats.rows_created += 1
                except Exception:
                    logger.exception("VWAP row creation failed for %s", sym)
            # Heartbeat every 10 samples
            if self._stats.samples % 10 == 0:
                logger.info(
                    "VWAP capture heartbeat: samples=%s rows=%s",
                    self._stats.samples,
                    self._stats.rows_created,
                )
            self._stop_event.wait(self.interval_seconds)


_capture_service = VWAPMinuteCaptureService(interval_seconds=_capture_interval())


def start_vwap_capture_service() -> bool:
    return _capture_service.start()


def stop_vwap_capture_service(wait: bool = False) -> bool:
    return _capture_service.stop(wait=wait)


def is_vwap_capture_running() -> bool:
    thread = _capture_service._thread
    return bool(thread and thread.is_alive())


__all__ = [
    "start_vwap_capture_service",
    "stop_vwap_capture_service",
    "is_vwap_capture_running",
    "VWAPMinuteCaptureService",
]
