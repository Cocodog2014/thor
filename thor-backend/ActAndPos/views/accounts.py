"""Unified accounts endpoint combining live and paper accounts."""

from decimal import Decimal
from typing import Any

from rest_framework.decorators import api_view
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response

from ActAndPos.live.models import LiveBalance
from ActAndPos.paper.models import PaperBalance


def _require_user(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise NotAuthenticated("Authentication required")
    return user


def _default_account_key(user) -> str:
    return f"PAPER-{getattr(user, 'pk', '0')}"


@api_view(["GET"])
def accounts_view(request):
    """GET /actandpos/accounts

    Return a unified list of all accounts (live + paper) for the authenticated user.
    Combines data from LiveBalance (live accounts) and PaperBalance (paper accounts).
    """

    user = _require_user(request)
    accounts: list[dict[str, Any]] = []

    # --- Live Accounts (from LiveBalance) ---
    live_balances = LiveBalance.objects.filter(user=user).order_by(
        "broker", "broker_account_id"
    )
    for lb in live_balances:
        accounts.append(
            {
                "id": str(lb.broker_account_id),
                "broker": lb.broker,
                "broker_account_id": str(lb.broker_account_id),
                "account_number": None,  # Could be extended if stored on LiveBalance
                "display_name": lb.broker_account_id or "Live Account",
                "currency": lb.currency or "USD",
                "net_liq": str(lb.net_liq or Decimal("0")),
                "cash": str(lb.cash or Decimal("0")),
                "equity": str(lb.equity or Decimal("0")),
                "ok_to_trade": True,
            }
        )

    # --- Paper Accounts (from PaperBalance) ---
    default_key = _default_account_key(user)
    paper_keys = set(
        PaperBalance.objects.filter(user=user).values_list("account_key", flat=True)
    )
    paper_keys.add(default_key)

    for key in sorted(paper_keys):
        # Try to get balance data if available
        pb = PaperBalance.objects.filter(user=user, account_key=key).first()
        accounts.append(
            {
                "id": key,
                "broker": "PAPER",
                "broker_account_id": key,
                "account_number": None,
                "display_name": "Paper Trading" if key == default_key else key,
                "currency": "USD",
                "net_liq": str(pb.net_liq if pb else Decimal("0")),
                "cash": str(pb.cash if pb else Decimal("0")),
                "equity": str(pb.equity if pb else Decimal("0")),
                "ok_to_trade": True,
            }
        )

    return Response(accounts)
