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
    """Pick account via ?account_id query parameter or return the first record."""

    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise NotAuthenticated("Authentication required to access trading accounts.")

    account_id = request.query_params.get("account_id")
    qs = Account.objects.filter(user=user).order_by("id")

    if account_id:
        return get_object_or_404(qs, pk=account_id)

    account = qs.first()
    if account is None:
        account = _create_default_paper_account(user)
    return account


@api_view(["GET"])
def account_summary_view(request):
    """Return a simple account summary payload for the selected account."""

    account = get_active_account(request)
    return Response(AccountSummarySerializer(account).data)
