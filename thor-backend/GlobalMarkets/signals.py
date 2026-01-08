"""
GlobalMarkets signals

Emits events when a Market's status changes.
Other apps (e.g. FutureTrading) can listen to these
without GlobalMarkets knowing about them.
"""

import logging
from django.db.models.signals import pre_save
from django.dispatch import receiver, Signal
from .models import Market

logger = logging.getLogger(__name__)

# Custom signals other apps can subscribe to
market_status_changed = Signal()  # args: instance, previous_status, new_status
market_opened = Signal()          # args: instance
market_closed = Signal()          # args: instance


@receiver(pre_save, sender=Market)
def on_market_status_change(sender, instance: Market, **kwargs):
    """
    Fire signals when a Market's status actually changes.

    Does NOT trigger any capturing itself – it just broadcasts events.
    """
    # New object being created – no "previous" status to compare to
    if not instance.pk:
        return

    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        # Should not happen, but fail safe
        return

    prev_status = previous.status
    new_status = instance.status

    if prev_status == new_status:
        # No real status change
        return

    logger.info(
    "Market %s status changed: %s → %s",
    instance.key,
    prev_status,
    new_status,
)


    # Emit generic status-changed signal
    market_status_changed.send(
        sender=sender,
        instance=instance,
        previous_status=prev_status,
        new_status=new_status,
    )

    # Emit convenience signals
    if new_status == "OPEN":
        market_opened.send(sender=sender, instance=instance)
    elif new_status == "CLOSED":
        market_closed.send(sender=sender, instance=instance)
