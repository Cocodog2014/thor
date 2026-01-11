from __future__ import annotations

from rest_framework.decorators import api_view
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response

from ActAndPos.shared.accounts import (
    iter_accounts_for_user,
    resolve_account_for_user,
    serialize_active_account,
)


@api_view(["GET"])
def accounts_view(request):
    """GET /api/actandpos/accounts

    Unified account list combining paper + live domains.
    """

    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise NotAuthenticated("Authentication required")

    # Ensure every user sees at least one PAPER account.
    try:
        resolve_account_for_user(user=user, account_id=None)
    except Exception:
        pass

    accounts = [
        serialize_active_account(request=request, account=acct)
        for acct in iter_accounts_for_user(user)
    ]
    return Response({"accounts": accounts})
