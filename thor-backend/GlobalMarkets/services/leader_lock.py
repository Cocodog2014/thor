"""Simple Redis-based leader lock with periodic renewal."""
from __future__ import annotations

import logging
import time
from typing import Optional

from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


class LeaderLock:
    """
    Redis leader lock.

    IMPORTANT:
    - redis-py Lock stores the token in thread-local storage.
    - Therefore renew/extend MUST occur in the same thread that acquired the lock.
    """

    def __init__(self, key: str, ttl_seconds: int = 30, renew_every: Optional[float] = None) -> None:
        self.key = key
        self.ttl = int(ttl_seconds)
        self.renew_every = renew_every if renew_every is not None else max(1.0, self.ttl * 0.5)

        self._lock = live_data_redis.client.lock(name=key, timeout=self.ttl)
        self._acquired = False
        self._last_renew = 0.0

    @property
    def acquired(self) -> bool:
        return self._acquired

    def acquire(self, blocking: bool = False, timeout: float = 0) -> bool:
        try:
            blocking_timeout = timeout if timeout > 0 else None
            got = self._lock.acquire(blocking=blocking, blocking_timeout=blocking_timeout)
        except Exception:
            logger.exception("Leader lock acquire failed for %s", self.key)
            return False

        if not got:
            return False

        self._acquired = True
        self._last_renew = time.monotonic()
        return True

    def renew_if_due(self) -> bool:
        """
        Extend lock TTL if renew interval has passed.
        Must be called from the same thread that acquired the lock.
        Returns False if renew failed (caller should stop work).
        """
        if not self._acquired:
            return False

        now = time.monotonic()
        if (now - self._last_renew) < self.renew_every:
            return True

        try:
            # extend by ttl seconds
            self._lock.extend(self.ttl)
            self._last_renew = now
            return True
        except Exception:
            logger.exception("Leader lock renew failed for %s", self.key)
            return False

    def release(self) -> None:
        if not self._acquired:
            return
        try:
            self._lock.release()
        except Exception:
            logger.exception("Leader lock release failed for %s", self.key)
        finally:
            self._acquired = False

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
