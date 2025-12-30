# ThorTrading/intraday/redis_gateway.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from LiveData.shared.redis_client import live_data_redis


@dataclass(frozen=True)
class ActiveSessions:
    futures: Optional[str]
    equities: Optional[str]


def get_active_sessions() -> ActiveSessions:
    """
    Returns the currently-active routing session keys (written by GlobalMarkets).
    """
    futures = live_data_redis.get_active_session_key(asset_type="futures")
    equities = live_data_redis.get_active_session_key(asset_type="equities")
    return ActiveSessions(futures=futures, equities=equities)
