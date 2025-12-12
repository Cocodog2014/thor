"""Signal handlers that enforce ActAndPos invariants.

Currently, the only invariant is: every user must own at least one paper
trading account so the UI can function immediately after signup. By wiring
this at the signal level we guarantee admin-created users, fixtures, and
tests all receive the default account without hitting specific views.
"""

from __future__ import annotations

from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


def _generate_paper_account_id(user) -> str:
    user_id = getattr(user, "pk", "NOUSER")
    return f"PAPER-{user_id}-{uuid4().hex[:8].upper()}"


def _create_default_paper_account(user):
    Account = apps.get_model("ActAndPos", "Account")
    return Account.objects.create(
        user=user,
        broker="PAPER",
        broker_account_id=_generate_paper_account_id(user),
        display_name="Paper Trading (Auto)",
    )


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_default_paper_account(sender, instance, created, **kwargs):
    """Automatically seed a paper account for every new user."""

    if not created:
        return

    Account = apps.get_model("ActAndPos", "Account")
    if Account.objects.filter(user=instance, broker="PAPER").exists():
        return

    _create_default_paper_account(instance)
