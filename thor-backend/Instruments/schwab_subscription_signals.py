"""Subscription → live stream control bridge.

This module lives in Instruments because it represents *product state* (what we track).

It publishes a tiny JSON control message to Redis whenever a user's subscriptions change,
so the `schwab_stream` management command can add/remove symbols without restart.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from Instruments.models import SchwabSubscription
from LiveData.schwab.control_plane import publish_symbol
from LiveData.schwab.signal_control import signals_suppressed


def _safe_symbol(value: Any) -> str:
    return str(value or "").strip().upper()


def _safe_asset(value: Any) -> str:
    return str(value or "").strip().upper()


def _publish_control(*, user_id: int, action: str, asset: str, symbol: str) -> None:
    publish_symbol(user_id=user_id, action=action, asset=asset, symbol=symbol)


@receiver(pre_save, sender=SchwabSubscription)
def schwab_subscription_pre_save(sender, instance: SchwabSubscription, **kwargs) -> None:
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
    if signals_suppressed() or not bool(getattr(settings, "SCHWAB_SUBSCRIPTION_SIGNAL_PUBLISH", False)):
        return

    symbol = _safe_symbol(instance.symbol)
    asset = _safe_asset(instance.asset_type)
    if not symbol or not asset:
        return

    prev: Optional[Dict[str, Any]] = getattr(instance, "_schwab_prev", None)

    def on_commit_publish() -> None:
        if created:
            if instance.enabled:
                _publish_control(user_id=instance.user_id, action="add", asset=asset, symbol=symbol)
            return

        if not prev:
            _publish_control(
                user_id=instance.user_id,
                action="add" if instance.enabled else "remove",
                asset=asset,
                symbol=symbol,
            )
            return

        prev_enabled = bool(prev.get("enabled"))
        prev_symbol = _safe_symbol(prev.get("symbol"))
        prev_asset = _safe_asset(prev.get("asset_type"))

        if prev_enabled and not instance.enabled:
            if prev_symbol and prev_asset:
                _publish_control(user_id=instance.user_id, action="remove", asset=prev_asset, symbol=prev_symbol)
            return

        if (not prev_enabled) and instance.enabled:
            _publish_control(user_id=instance.user_id, action="add", asset=asset, symbol=symbol)
            return

        if instance.enabled:
            if prev_symbol and prev_asset and (prev_symbol != symbol or prev_asset != asset):
                _publish_control(user_id=instance.user_id, action="remove", asset=prev_asset, symbol=prev_symbol)
                _publish_control(user_id=instance.user_id, action="add", asset=asset, symbol=symbol)

    transaction.on_commit(on_commit_publish)


@receiver(post_delete, sender=SchwabSubscription)
def schwab_subscription_post_delete(sender, instance: SchwabSubscription, **kwargs) -> None:
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
