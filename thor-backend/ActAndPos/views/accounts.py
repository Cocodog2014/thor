from uuid import uuid4

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response

from ..models import Account
from ..serializers import AccountSummarySerializer


def _create_default_paper_account(user) -> Account:
    """Bootstrap a default PAPER account so the UI always has data."""

    user_id = getattr(user, "pk", None) or "NOUSER"
    broker_account_id = f"PAPER-{user_id}-{uuid4().hex[:8].upper()}"
    return Account.objects.create(
        user=user,
        broker="PAPER",
        broker_account_id=broker_account_id,
        display_name="Paper Trading (Auto)",
    )


def get_active_account(request):
    """Pick account via ?account_id query parameter.

    If no account_id is provided, prefer a SCHWAB account (most recently updated)
    when one exists; otherwise fall back to the first account for this user.
    """

    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise NotAuthenticated("Authentication required to access trading accounts.")

    params = getattr(request, "query_params", None) or getattr(request, "GET", {})
    account_id = params.get("account_id")
    qs = Account.objects.filter(user=user)

    if account_id:
        # Accept either DB pk (int) or broker_account_id (e.g., Schwab hash)
        account = None
        try:
            account_pk = int(account_id)
            account = qs.filter(pk=account_pk).first()
        except (TypeError, ValueError):
            account = None

        if account is None:
            account = qs.filter(broker_account_id=account_id).first()

        if account is None:
            # fall back to 404 using broker_account_id for clarity
            return get_object_or_404(qs, broker_account_id=account_id)
        return account

    # Default selection: prefer a SCHWAB account when present.
    account = (
        qs.filter(broker="SCHWAB")
        .order_by("-updated_at", "id")
        .first()
    )
    if account is None:
        account = qs.order_by("id").first()
    if account is None:
        account = _create_default_paper_account(user)
    return account


@api_view(["GET"])
def account_summary_view(request):
    """Return a simple account summary payload for the selected account."""

    account = get_active_account(request)
    return Response(AccountSummarySerializer(account).data)
