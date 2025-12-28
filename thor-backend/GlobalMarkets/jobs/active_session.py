"""Publish active session routing for LiveData consumers.

Writes a small JSON blob to Redis so streaming producers can route
ticks/bars by session_key without guessing country defaults.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from django.utils import timezone

from GlobalMarkets.services.active_markets import get_control_markets
from LiveData.shared.redis_client import live_data_redis
from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.services.config.country_codes import normalize_country_code

logger = logging.getLogger(__name__)

ACTIVE_SESSION_KEY_REDIS = "live_data:active_session"
ACTIVE_SESSION_TTL_SECONDS = 10


class PublishActiveSessionJob:
    """Heartbeat job that publishes the active session routing snapshot."""

    name = "gm.publish_active_session"

    def _build_session_key(self, session: MarketSession, country: str) -> Optional[str]:
        if not session or session.session_number is None:
            return None

        normalized_country = normalize_country_code(country) or country

        year = session.year
        month = session.month
        day = session.date

        # Fall back to captured_at when explicit fields are missing
        captured_at = getattr(session, "captured_at", None)
        if captured_at:
            year = year or captured_at.year
            month = month or captured_at.month
            day = day or captured_at.day

        # Absolute fallback to current date to avoid empty payloads
        now = timezone.now()
        year = year or now.year
        month = month or now.month
        day = day or now.day

        try:
            return f"{normalized_country}:{year:04d}{month:02d}{day:02d}:{int(session.session_number)}"
        except Exception:
            logger.debug("Failed to format session_key for %s", normalized_country, exc_info=True)
            return None

    def _latest_session_key(self, country: str) -> Optional[str]:
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

        session_key = None
        for market in markets:
            if not getattr(market, "enable_session_capture", True):
                continue

            session_key = self._latest_session_key(getattr(market, "country", None))
            if session_key:
                break

        if not session_key:
            self._clear()
            return

        payload = {
            "default": session_key,
            "equities": session_key,
            "futures": session_key,
            "updated_at": time.time(),
        }

        try:
            live_data_redis.set_json(ACTIVE_SESSION_KEY_REDIS, payload, ex=ACTIVE_SESSION_TTL_SECONDS)
        except Exception:
            logger.debug("Failed to write %s", ACTIVE_SESSION_KEY_REDIS, exc_info=True)


__all__ = ["PublishActiveSessionJob"]