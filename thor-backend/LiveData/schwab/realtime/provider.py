"""Schwab realtime job provider for the heartbeat scheduler.

Keeps Schwab access tokens fresh and publishes health snapshots.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from django.conf import settings

from api.websocket.broadcast import broadcast_to_websocket_sync
from core.infra.jobs import Job
from LiveData.schwab.models import BrokerConnection
from LiveData.schwab.tokens import ensure_valid_access_token
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


class SchwabHealthJob(Job):
    name = "schwab_health"

    def __init__(self, interval_seconds: float = 15.0, refresh_buffer_seconds: int | None = None):
        # Default to 120s buffer; allow override via settings/env
        default_buffer = getattr(settings, "SCHWAB_HEARTBEAT_BUFFER_SECONDS", 120)
        self.interval_seconds = float(interval_seconds)
        self.refresh_buffer_seconds = int(refresh_buffer_seconds or default_buffer)

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def _snapshot(self, conn: BrokerConnection, *, refreshed: bool, error: str | None) -> dict[str, Any]:
        now_ts = int(time.time())
        expires_at = int(getattr(conn, "access_expires_at", 0) or 0)
        seconds_left = max(0, expires_at - now_ts)
        return {
            "user_id": conn.user_id,
            "broker": conn.broker,
            "account_id": conn.broker_account_id or None,
            "trading_enabled": bool(conn.trading_enabled),
            "expires_at": expires_at,
            "seconds_until_expiry": seconds_left,
            "token_expired": expires_at <= now_ts,
            "refreshed": refreshed,
            "error": error,
        }

    def run(self, ctx: Any) -> None:
        now_ts = int(time.time())
        connections = (
            BrokerConnection.objects.filter(broker=BrokerConnection.BROKER_SCHWAB)
            .select_related("user")
        )

        rows: list[dict[str, Any]] = []
        refreshed_count = 0

        for conn in connections:
            refreshed = False
            error = None
            try:
                expires_at = int(conn.access_expires_at or 0)
                seconds_left = max(0, expires_at - now_ts)

                if seconds_left <= self.refresh_buffer_seconds:
                    conn = ensure_valid_access_token(
                        conn,
                        buffer_seconds=self.refresh_buffer_seconds,
                        force_refresh=seconds_left <= self.refresh_buffer_seconds,
                    )
                    refreshed = True
                    refreshed_count += 1
            except Exception as exc:  # noqa: BLE001
                error = str(exc)
                logger.warning("schwab_health: refresh failed for user_id=%s: %s", conn.user_id, exc, exc_info=True)
            finally:
                rows.append(self._snapshot(conn, refreshed=refreshed, error=error))

        payload = {"timestamp": now_ts, "connections": rows}

        try:
            live_data_redis.client.setex(
                "live_data:schwab:health",
                60,
                json.dumps(payload, default=str),
            )
        except Exception:
            logger.debug("schwab_health: failed to cache Redis payload", exc_info=True)

        try:
            broadcast_to_websocket_sync(
                getattr(ctx, "channel_layer", None) if ctx else None,
                {"type": "schwab_health", "data": payload},
            )
        except Exception:
            logger.debug("schwab_health: websocket broadcast failed", exc_info=True)

        if refreshed_count:
            logger.info("schwab_health: refreshed Schwab tokens for %s connection(s)", refreshed_count)


def register(registry):
    job = SchwabHealthJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    return [job.name]


__all__ = ["register", "SchwabHealthJob"]
