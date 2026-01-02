"""Publish active session routing for LiveData consumers.

Writes a small JSON blob to Redis so streaming producers can route
ticks/bars by session_key without guessing country defaults.
"""
from __future__ import annotations

import logging
import time
from typing import Optional
from GlobalMarkets.services.active_markets import get_control_markets
from LiveData.shared.redis_client import live_data_redis
from ThorTrading.models.MarketSession import MarketSession
from GlobalMarkets.services.normalize import normalize_country_code

logger = logging.getLogger(__name__)

ACTIVE_SESSION_KEY_REDIS = "live_data:active_session"
ACTIVE_SESSION_TTL_SECONDS = 10


class PublishActiveSessionJob:
    """Heartbeat job that publishes the active session routing snapshot."""

    name = "gm.publish_active_session"

    def _build_session_key(self, session: MarketSession, country: str) -> Optional[tuple[str, int]]:
        if not session or session.session_number is None:
            return None

        normalized_country = normalize_country_code(country) or country

        try:
            sn = int(session.session_number)
            return (f"session:{sn}", sn)
        except Exception:
            logger.debug("Failed to format session_key for %s", normalized_country, exc_info=True)
            return None

    def _latest_session_key(self, country: str) -> Optional[tuple[str, int]]:
        if not country:
            return None

        try:
            session = (
                MarketSession.objects
                .filter(country=normalize_country_code(country) or country)
                .exclude(session_number__isnull=True)
                .order_by("-captured_at", "-session_number")
                .first()
            )
        except Exception:
            logger.debug("Failed to query MarketSession for %s", country, exc_info=True)
            return None

        return self._build_session_key(session, country)

    def _clear(self) -> None:
        try:
            live_data_redis.client.delete(ACTIVE_SESSION_KEY_REDIS)
        except Exception:
            logger.debug("Failed to clear %s", ACTIVE_SESSION_KEY_REDIS, exc_info=True)

    def run(self, ctx=None) -> None:
        markets = list(get_control_markets(statuses={"OPEN"}))
        if not markets:
            self._clear()
            return

        markets.sort(key=lambda m: m.get_sort_order())

        session_info: Optional[tuple[str, int]] = None
        for market in markets:
            if not getattr(market, "enable_session_capture", True):
                continue

            session_info = self._latest_session_key(getattr(market, "country", None))
            if session_info:
                break

        if not session_info:
            self._clear()
            return

        payload = {
            "default": session_info[0],
            "equities": session_info[0],
            "futures": session_info[0],
            "session_number": session_info[1],
            "updated_at": time.time(),
        }

        try:
            live_data_redis.set_json(ACTIVE_SESSION_KEY_REDIS, payload, ex=ACTIVE_SESSION_TTL_SECONDS)
        except Exception:
            logger.debug("Failed to write %s", ACTIVE_SESSION_KEY_REDIS, exc_info=True)


__all__ = ["PublishActiveSessionJob"]
