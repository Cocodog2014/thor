from __future__ import annotations

import json
import logging

from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


def control_channel(user_id: int) -> str:
    # Must match schwab_stream.py
    return f"live_data:subscriptions:schwab:{int(user_id)}"


def publish_payload(*, user_id: int, payload: dict) -> None:
    try:
        live_data_redis.client.publish(control_channel(int(user_id)), json.dumps(payload))
    except Exception as exc:
        logger.warning("Schwab control publish failed (user_id=%s): %s", user_id, exc, exc_info=True)


def publish_set(*, user_id: int, asset: str, symbols: list[str]) -> None:
    publish_payload(
        user_id=user_id,
        payload={
            "action": "set",
            "asset": asset,
            "symbols": symbols,
        },
    )


def publish_symbol(*, user_id: int, action: str, asset: str, symbol: str) -> None:
    publish_payload(
        user_id=user_id,
        payload={
            "action": action,
            "asset": asset,
            "symbols": [symbol],
        },
    )
