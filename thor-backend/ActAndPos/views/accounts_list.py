# ActAndPos/views/accounts_list.py

from rest_framework.decorators import api_view
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response

from django.db.models import Case, IntegerField, Value, When

from ..models import Account
from ..serializers import AccountSummarySerializer


@api_view(["GET"])
def accounts_list_view(request):
    """
    GET /api/actandpos/accounts

    List all trading accounts (Schwab + Paper).
    """

    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise NotAuthenticated("Authentication required to list trading accounts.")

    qs = (
        Account.objects.filter(user=user)
        .select_related("user")
        .order_by(
            # Prefer SCHWAB accounts over PAPER for default UI selection.
            Case(
                When(broker="SCHWAB", then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            "-updated_at",
            "id",
        )
    )
    data = AccountSummarySerializer(qs, many=True).data
    return Response(data)
