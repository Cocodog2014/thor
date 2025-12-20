"""Signal → WebSocket bridge for GlobalMarkets.

Keeps WebSocket transport code centralized under api.websocket while
subscribing to GlobalMarkets signals.
"""
import logging
from typing import Any, Dict

from channels.layers import get_channel_layer
from django.dispatch import receiver

from api.websocket.broadcast import broadcast_to_websocket_sync
from api.websocket.messages import build_market_status_message
from GlobalMarkets.signals import market_status_changed

logger = logging.getLogger(__name__)


def _build_payload(instance: Any, status_data: Dict[str, Any]) -> Dict[str, Any]:
    """Shape the payload to match frontend expectations."""
    # Guarantee current_time so frontend clocks advance when WS updates arrive
    if status_data is not None:
        status_data.setdefault("current_time", None)
    return {
        "market_id": getattr(instance, "id", None),
        "id": getattr(instance, "id", None),
        "country": getattr(instance, "country", None),
        "status": getattr(instance, "status", None),
        "market_status": status_data,
        "current_time": status_data.get("current_time") if status_data else None,
    }


@receiver(market_status_changed)
def broadcast_market_status(sender, instance, **kwargs):
    """Broadcast market_status to WebSocket clients when status changes."""
    try:
        status_data = instance.get_market_status()
        if not status_data:
            return

        payload = _build_payload(instance, status_data)
        message = build_market_status_message(payload)
        channel_layer = get_channel_layer()
        broadcast_to_websocket_sync(channel_layer, message)
    except Exception:
        logger.exception(
            "Failed to broadcast market status for %s", getattr(instance, "country", "unknown")
        )
