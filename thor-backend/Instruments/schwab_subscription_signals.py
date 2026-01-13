"""Watchlist → live stream control bridge.

Instruments owns product state (what the user wants live):
    UserInstrumentWatchlistItem(enabled=True, stream=True)

This module publishes small control messages to Redis when watchlist rows change,
so the `schwab_stream` management command can converge without restart.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from Instruments.models import UserInstrumentWatchlistItem
from Instruments.services.watchlist_sync import sync_watchlist_to_schwab, sync_global_watchlist_to_schwab
from LiveData.schwab.signal_control import signals_suppressed


@receiver(post_save, sender=UserInstrumentWatchlistItem)
def watchlist_item_post_save(sender, instance: UserInstrumentWatchlistItem, created: bool, **kwargs) -> None:
    if signals_suppressed() or not bool(getattr(settings, "SCHWAB_SUBSCRIPTION_SIGNAL_PUBLISH", False)):
        return
    if not getattr(instance, "user_id", None):
        return

    mode_cls = getattr(UserInstrumentWatchlistItem, "Mode", None)
    live = getattr(mode_cls, "LIVE", "LIVE")
    global_mode = getattr(mode_cls, "GLOBAL", "GLOBAL")

    # PAPER list is UI-only; it should not drive Schwab streaming.
    if getattr(instance, "mode", None) == global_mode:
        transaction.on_commit(lambda: sync_global_watchlist_to_schwab())
        return

    if getattr(instance, "mode", None) != live:
        return

    # Publish full sets to avoid per-row drift and simplify convergence.
    transaction.on_commit(lambda: sync_watchlist_to_schwab(int(instance.user_id)))


@receiver(post_delete, sender=UserInstrumentWatchlistItem)
def watchlist_item_post_delete(sender, instance: UserInstrumentWatchlistItem, **kwargs) -> None:
    if signals_suppressed() or not bool(getattr(settings, "SCHWAB_SUBSCRIPTION_SIGNAL_PUBLISH", False)):
        return

    if not getattr(instance, "user_id", None):
        return

    mode_cls = getattr(UserInstrumentWatchlistItem, "Mode", None)
    live = getattr(mode_cls, "LIVE", "LIVE")
    global_mode = getattr(mode_cls, "GLOBAL", "GLOBAL")

    if getattr(instance, "mode", None) == global_mode:
        transaction.on_commit(lambda: sync_global_watchlist_to_schwab())
        return

    if getattr(instance, "mode", None) != live:
        return

    transaction.on_commit(lambda: sync_watchlist_to_schwab(int(instance.user_id)))
