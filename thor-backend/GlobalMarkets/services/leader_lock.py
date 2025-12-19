"""Simple Redis-based leader lock with periodic renewal."""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


class LeaderLock:
    def __init__(self, key: str, ttl_seconds: int = 30) -> None:
        self.key = key
        self.ttl = ttl_seconds
        self._lock = live_data_redis.client.lock(name=key, timeout=ttl_seconds)
        self._renew_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._acquired = False

    @property
    def acquired(self) -> bool:
        return self._acquired

    def acquire(self, blocking: bool = False, timeout: float = 0) -> bool:
        try:
            got = self._lock.acquire(blocking=blocking, timeout=timeout)
        except Exception:
            logger.exception("Leader lock acquire failed for %s", self.key)
            return False

        if not got:
            return False

        self._acquired = True
        self._start_renewal()
        return True

    def release(self) -> None:
        self._stop_event.set()
        if self._renew_thread and self._renew_thread.is_alive():
            self._renew_thread.join(timeout=2)
        if not self._acquired:
            return
        try:
            self._lock.release()
            self._acquired = False
        except Exception:
            logger.exception("Leader lock release failed for %s", self.key)

    def _start_renewal(self) -> None:
        def _renew_loop():
            interval = max(1.0, self.ttl * 0.5)
            while not self._stop_event.wait(interval):
                try:
                    self._lock.extend(self.ttl)
                except Exception:
                    logger.exception("Leader lock renew failed for %s", self.key)
                    break

        self._renew_thread = threading.Thread(target=_renew_loop, name=f"LeaderLock-{self.key}", daemon=True)
        self._renew_thread.start()

    def __enter__(self):
        self.acquire(blocking=True, timeout=5)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()


_monitor_leader_lock: Optional[LeaderLock] = None


def set_monitor_leader_lock(lock: LeaderLock) -> None:
    global _monitor_leader_lock
    _monitor_leader_lock = lock


def get_monitor_leader_lock() -> Optional[LeaderLock]:
    return _monitor_leader_lock
