"""Signal handlers that enforce ActAndPos invariants.

Currently, the only invariant is: every user must own at least one paper
trading account so the UI can function immediately after signup. By wiring
this at the signal level we guarantee admin-created users, fixtures, and
tests all receive the default account without hitting specific views.
"""

from __future__ import annotations

from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

PAPER_DEFAULT_BALANCE = Decimal("100000.00")


def _ensure_default_paper_balance(user) -> None:
    """Ensure every user has at least one PaperBalance row.

    After legacy ActAndPos.Account was removed, PAPER accounts are represented
    by PaperBalance/PaperPosition/PaperOrder rows keyed by account_key.
    """

    PaperBalance = apps.get_model("ActAndPos", "PaperBalance")
    if PaperBalance.objects.filter(user=user).exists():
        return

    account_key = f"PAPER-{getattr(user, 'pk', 'NOUSER')}"
    PaperBalance.objects.get_or_create(
        user=user,
        account_key=account_key,
        defaults={
            "currency": "USD",
            "cash": PAPER_DEFAULT_BALANCE,
            "equity": PAPER_DEFAULT_BALANCE,
            "net_liq": PAPER_DEFAULT_BALANCE,
            "buying_power": PAPER_DEFAULT_BALANCE,
            "day_trade_bp": PAPER_DEFAULT_BALANCE,
        },
    )


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_default_paper_account(sender, instance, created, **kwargs):
    """Automatically seed a paper account for every new user."""

    if not created:
        return

    _ensure_default_paper_balance(instance)
