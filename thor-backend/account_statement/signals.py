from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.contrib.auth import get_user_model

from .models import PaperAccount
from .models.real import RealAccount


def ensure_user_paper_account(user) -> PaperAccount | None:
    """Create a PaperAccount for the user if one does not already exist.

    Returns the created PaperAccount or None if it already existed.
    """
    if PaperAccount.objects.filter(user=user).exists():
        return None
    with transaction.atomic():
        acct = PaperAccount.objects.create(user=user)
    return acct


def ensure_user_real_account(user) -> RealAccount | None:
    """Create a RealAccount stub for the user if one does not already exist.

    Returns the created RealAccount or None if it already existed.
    """
    if RealAccount.objects.filter(user=user).exists():
        return None
    with transaction.atomic():
        acct = RealAccount.objects.create(user=user)
    return acct


@receiver(user_logged_in)
def auto_provision_paper_account_on_login(sender, user, request, **kwargs):
    """Auto-create a paper account for the user on first login.

    This ensures every authenticated user has a paper trading sandbox
    without any manual setup.
    """
    try:
        ensure_user_paper_account(user)
    except Exception:
        # Avoid blocking login on any unexpected error
        # (Could add logging here if a logger is configured)
        pass


@receiver(post_save, sender=get_user_model())
def auto_provision_accounts_on_user_create(sender, instance, created, **kwargs):
    """Ensure each new user receives their own Paper and Real accounts on registration."""
    if not created:
        return
    try:
        ensure_user_paper_account(instance)
    except Exception:
        pass
    try:
        ensure_user_real_account(instance)
    except Exception:
        pass
