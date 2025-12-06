# ActAndPos/views/accounts_list.py

from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Account
from ..serializers import AccountSummarySerializer


@api_view(["GET"])
def accounts_list_view(request):
    """
    GET /api/actandpos/accounts

    List all trading accounts (Schwab + Paper).
    """

    qs = Account.objects.all().order_by("broker", "display_name", "broker_account_id")
    data = AccountSummarySerializer(qs, many=True).data
    return Response(data)
