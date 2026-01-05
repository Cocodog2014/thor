"""Schwab subscription → live stream control bridge.

What this file does
-------------------
This module hooks Django model signals for `SchwabSubscription` and publishes a small JSON
control message to Redis whenever a user’s subscriptions change (create/update/delete).

The `schwab_stream` management command already listens on:
    live_data:schwab:control:<user_id>

So the end-to-end behavior is:
- Admin add / enable / edit / delete subscription → publish control message → streamer adjusts
    without restarting the streaming process.

Why this file is “small” (vs the mis-done one)
----------------------------------------------
The earlier large file (named `signals,py` with a comma) appears to be an accidental copy of
the streaming management command. Streaming + reconnect logic belongs in
`management/commands/schwab_stream.py`.

This `signals.py` is intentionally tiny because it only needs to:
- detect changes
- serialize a message
- publish to Redis

Safety/production notes
-----------------------
- Uses `transaction.on_commit()` so we only publish after the DB change is committed.
- Never raises on Redis errors (admin saves should still succeed if Redis is down).
"""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from django.conf import settings

from LiveData.schwab.control_plane import publish_symbol
from LiveData.schwab.models import SchwabSubscription
from LiveData.schwab.signal_control import signals_suppressed

logger = logging.getLogger(__name__)


def _safe_symbol(value: Any) -> str:
    return str(value or "").strip().upper()


def _safe_asset(value: Any) -> str:
    return str(value or "").strip().upper()


def _publish_control(*, user_id: int, action: str, asset: str, symbol: str) -> None:
    """Publish a single-symbol control message to the schwab streamer control plane."""
    publish_symbol(user_id=user_id, action=action, asset=asset, symbol=symbol)


@receiver(pre_save, sender=SchwabSubscription)
def schwab_subscription_pre_save(sender, instance: SchwabSubscription, **kwargs) -> None:
    """Capture previous values so post_save can emit correct add/remove events."""

    if signals_suppressed() or not bool(getattr(settings, "SCHWAB_SUBSCRIPTION_SIGNAL_PUBLISH", False)):
        instance._schwab_prev = None  # type: ignore[attr-defined]
        return

    if instance.pk is None:
        instance._schwab_prev = None  # type: ignore[attr-defined]
        return

    prev: Optional[Dict[str, Any]] = (
        sender.objects.filter(pk=instance.pk).values("symbol", "asset_type", "enabled", "user_id").first()
    )
    instance._schwab_prev = prev  # type: ignore[attr-defined]


@receiver(post_save, sender=SchwabSubscription)
def schwab_subscription_post_save(
    sender,
    instance: SchwabSubscription,
    created: bool,
    **kwargs,
) -> None:
    """Publish Redis control messages when subscriptions change via Admin/API."""

    if signals_suppressed() or not bool(getattr(settings, "SCHWAB_SUBSCRIPTION_SIGNAL_PUBLISH", False)):
        return

    symbol = _safe_symbol(instance.symbol)
    asset = _safe_asset(instance.asset_type)

    if not symbol or not asset:
        return

    prev: Optional[Dict[str, Any]] = getattr(instance, "_schwab_prev", None)

    def on_commit_publish() -> None:
        # CREATE
        if created:
            if instance.enabled:
                _publish_control(user_id=instance.user_id, action="add", asset=asset, symbol=symbol)
            return

        # UPDATE (best-effort; if we couldn't load prev state, fall back to enabled-based add/remove)
        if not prev:
            if instance.enabled:
                _publish_control(user_id=instance.user_id, action="add", asset=asset, symbol=symbol)
            else:
                _publish_control(user_id=instance.user_id, action="remove", asset=asset, symbol=symbol)
            return

        prev_enabled = bool(prev.get("enabled"))
        prev_symbol = _safe_symbol(prev.get("symbol"))
        prev_asset = _safe_asset(prev.get("asset_type"))

        # Enabled toggle
        if prev_enabled and not instance.enabled:
            if prev_symbol and prev_asset:
                _publish_control(user_id=instance.user_id, action="remove", asset=prev_asset, symbol=prev_symbol)
            return

        if (not prev_enabled) and instance.enabled:
            _publish_control(user_id=instance.user_id, action="add", asset=asset, symbol=symbol)
            return

        # Still enabled: handle symbol/asset edits
        if instance.enabled:
            if prev_symbol and prev_asset and (prev_symbol != symbol or prev_asset != asset):
                _publish_control(user_id=instance.user_id, action="remove", asset=prev_asset, symbol=prev_symbol)
                _publish_control(user_id=instance.user_id, action="add", asset=asset, symbol=symbol)

    transaction.on_commit(on_commit_publish)


@receiver(post_delete, sender=SchwabSubscription)
def schwab_subscription_post_delete(sender, instance: SchwabSubscription, **kwargs) -> None:
    """Publish remove when a subscription row is deleted."""

    if signals_suppressed() or not bool(getattr(settings, "SCHWAB_SUBSCRIPTION_SIGNAL_PUBLISH", False)):
        return

    if not instance.enabled:
        return

    symbol = _safe_symbol(instance.symbol)
    asset = _safe_asset(instance.asset_type)

    if not symbol or not asset:
        return

    transaction.on_commit(
        lambda: _publish_control(user_id=instance.user_id, action="remove", asset=asset, symbol=symbol)
    )
