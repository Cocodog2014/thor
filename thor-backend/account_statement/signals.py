from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.db import transaction

from .models import PaperAccount


def ensure_user_paper_account(user) -> PaperAccount | None:
    """Create a PaperAccount for the user if one does not already exist.

    Returns the created PaperAccount or None if it already existed.
    """
    if PaperAccount.objects.filter(user=user).exists():
        return None
    with transaction.atomic():
        acct = PaperAccount.objects.create(user=user)
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
