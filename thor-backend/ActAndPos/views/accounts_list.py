from rest_framework.decorators import api_view
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response

from .accounts import _iter_accounts_for_user, serialize_active_account


@api_view(["GET"])
def accounts_list_view(request):
    """
    GET /api/actandpos/accounts

    List all trading accounts (Schwab + Paper).
    """

    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise NotAuthenticated("Authentication required to list trading accounts.")

    accounts = list(_iter_accounts_for_user(user))

    # Prefer SCHWAB first, then stable id sort.
    def _sort_key(a):
        return (0 if str(a.broker).upper() == "SCHWAB" else 1, str(a.id))

    accounts.sort(key=_sort_key)

    data = [serialize_active_account(request=request, account=a) for a in accounts]
    return Response(data)
