from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Account
from ..serializers import AccountSummarySerializer


def get_active_account(request):
    """Pick account via ?account_id query parameter or return the first record."""

    account_id = request.query_params.get("account_id")
    if account_id:
        return get_object_or_404(Account, pk=account_id)

    account = Account.objects.first()
    if account is None:
        raise ValueError("No accounts defined.")
    return account


@api_view(["GET"])
def account_summary_view(request):
    """Return a simple account summary payload for the selected account."""

    try:
        account = get_active_account(request)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)

    return Response(AccountSummarySerializer(account).data)
