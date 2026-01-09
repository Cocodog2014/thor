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
from LiveData.schwab.client.tokens import ensure_valid_access_token
from LiveData.shared.redis_client import live_data_redis
from thor_project.realtime.broadcaster import maybe_broadcast_global_market_status

logger = logging.getLogger(__name__)


class MarketDataSnapshotJob(Job):
    name = "market_data_snapshot"

    def __init__(
        self,
        interval_seconds: float = 1.0,
        *,
        active_window_seconds: int = 60,
        prune_after_seconds: int = 300,
        max_symbols: int = 500,
    ):
        self.interval_seconds = float(interval_seconds)
        self.active_window_seconds = int(active_window_seconds)
        self.prune_after_seconds = int(prune_after_seconds)
        self.max_symbols = int(max_symbols)

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        now_ts = int(time.time())

        # Prune old symbols and pull the active set from Redis.
        try:
            zkey = live_data_redis.ACTIVE_QUOTES_ZSET
            live_data_redis.client.zremrangebyscore(zkey, 0, now_ts - self.prune_after_seconds)
            symbols = live_data_redis.client.zrevrangebyscore(
                zkey,
                "+inf",
                now_ts - self.active_window_seconds,
                start=0,
                num=self.max_symbols,
            )
        except Exception:
            logger.debug("market_data_snapshot: failed reading active symbols", exc_info=True)
            return

        if not symbols:
            return

        # Pull quote snapshots in one HMGET.
        quotes: list[dict[str, Any]] = []
        try:
            raws = live_data_redis.client.hmget(live_data_redis.LATEST_QUOTES_HASH, *symbols)
            for raw in raws:
                if not raw:
                    continue
                try:
                    q = json.loads(raw)
                    if isinstance(q, dict):
                        quotes.append(q)
                except Exception:
                    continue
        except Exception:
            logger.debug("market_data_snapshot: failed reading latest quotes", exc_info=True)
            return

        if not quotes:
            return

        payload = {"timestamp": now_ts, "quotes": quotes}

        try:
            live_data_redis.client.setex("thor:market_data:snapshot", 10, json.dumps(payload, default=str))
        except Exception:
            logger.debug("market_data_snapshot: failed caching snapshot", exc_info=True)

        try:
            broadcast_to_websocket_sync(
                getattr(ctx, "channel_layer", None) if ctx else None,
                {"type": "market_data", "data": payload},
            )
        except Exception:
            logger.debug("market_data_snapshot: websocket broadcast failed", exc_info=True)


class SchwabHealthJob(Job):
    name = "schwab_health"

    def __init__(self, interval_seconds: float | None = None, refresh_buffer_seconds: int | None = None):
        # Defaults read from settings with sensible fallbacks
        default_buffer = getattr(settings, "SCHWAB_HEARTBEAT_BUFFER_SECONDS", 120)
        default_interval = getattr(settings, "SCHWAB_HEALTH_INTERVAL", 15)

        self.interval_seconds = float(interval_seconds or default_interval)
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

            # Skip unusable records early to avoid noisy refresh attempts
            if not conn.refresh_token:
                rows.append(self._snapshot(conn, refreshed=False, error="missing refresh_token"))
                continue
            try:
                expires_at = int(conn.access_expires_at or 0)
                seconds_left = max(0, expires_at - now_ts)

                if seconds_left <= self.refresh_buffer_seconds:
                    conn = ensure_valid_access_token(
                        conn,
                        buffer_seconds=self.refresh_buffer_seconds,
                        force_refresh=False,
                    )
                    # If a refresh actually occurred, ensure_valid_access_token would have saved/updated
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


class GlobalMarketsStatusBroadcastJob(Job):
    """Compute market status periodically and broadcast ONLY on change."""

    name = "global_markets_status_broadcast"

    def __init__(self, interval_seconds: float = 1.0):
        self.interval_seconds = float(interval_seconds)

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        try:
            maybe_broadcast_global_market_status()
        except Exception:
            logger.debug("global_markets_status_broadcast: failed", exc_info=True)


def register(registry):
    job = SchwabHealthJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    snapshot_job = MarketDataSnapshotJob(interval_seconds=1.0)
    registry.register(snapshot_job, interval_seconds=snapshot_job.interval_seconds)
    gm_job = GlobalMarketsStatusBroadcastJob(interval_seconds=1.0)
    registry.register(gm_job, interval_seconds=gm_job.interval_seconds)
    return [job.name, snapshot_job.name, gm_job.name]


__all__ = ["register", "SchwabHealthJob", "MarketDataSnapshotJob", "GlobalMarketsStatusBroadcastJob"]
