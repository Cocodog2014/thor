from uuid import uuid4

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Account
from ..serializers import AccountSummarySerializer


def _create_default_paper_account() -> Account:
    """Bootstrap a default PAPER account so the UI always has data."""

    broker_account_id = f"PAPER-DEMO-{uuid4().hex[:8].upper()}"
    return Account.objects.create(
        broker="PAPER",
        broker_account_id=broker_account_id,
        display_name="Paper Trading (Auto)",
    )


def get_active_account(request):
    """Pick account via ?account_id query parameter or return the first record."""

    account_id = request.query_params.get("account_id")
    if account_id:
        return get_object_or_404(Account, pk=account_id)

    account = Account.objects.order_by("id").first()
    if account is None:
        account = _create_default_paper_account()
    return account


@api_view(["GET"])
def account_summary_view(request):
    """Return a simple account summary payload for the selected account."""

    try:
        account = get_active_account(request)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)

    return Response(AccountSummarySerializer(account).data)
