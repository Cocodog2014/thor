"""Shared cross-domain views.

Views that don't belong to paper or live specifically but serve
both domains or aggregate across them.
"""
from __future__ import annotations

from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import NotAuthenticated

from ..paper.models import PaperBalance
from ..live.models import LiveBalance


@api_view(["GET"])
def account_balance_view(request):
    """GET /api/accounts/balance/
    
    Aggregates both paper and live balances for the authenticated user.
    Respects ?account_id=... and returns the balance for that account.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise NotAuthenticated("Authentication required")

    # Resolve active account (paper/live) using the same rules as ActAndPos.
    from ActAndPos.shared.accounts import get_active_account

    acct = get_active_account(request)
    now_iso = timezone.now().isoformat()

    if str(acct.broker).upper() == "PAPER":
        bal = PaperBalance.objects.filter(user=user, account_key=str(acct.broker_account_id)).order_by("-updated_at").first()
        if bal is None:
            # Ensure a default paper balance exists (best-effort).
            try:
                from ActAndPos.shared.accounts import resolve_account_for_user

                resolve_account_for_user(user=user, account_id=None)
            except Exception:
                pass
            bal = PaperBalance.objects.filter(user=user, account_key=str(acct.broker_account_id)).order_by("-updated_at").first()

        if bal is None:
            return Response({"detail": "Balance not found"}, status=404)

        return Response(
            {
                "account_id": str(bal.account_key),
                "net_liquidation": float(bal.net_liq or 0),
                "equity": float(bal.equity or 0),
                "cash": float(bal.cash or 0),
                "buying_power": float(bal.buying_power or 0),
                "day_trade_bp": float(bal.day_trade_bp or 0),
                "updated_at": bal.updated_at.isoformat() if bal.updated_at else now_iso,
                "source": "paper",
            }
        )

    bal = LiveBalance.objects.filter(
        user=user,
        broker=str(acct.broker or "SCHWAB").upper(),
        broker_account_id=str(acct.broker_account_id),
    ).order_by("-updated_at").first()

    if bal is None:
        return Response({"detail": "Balance not found"}, status=404)

    return Response(
        {
            "account_id": str(bal.broker_account_id),
            "net_liquidation": float(bal.net_liq or 0),
            "equity": float(bal.equity or 0),
            "cash": float(bal.cash or 0),
            "buying_power": float(bal.stock_buying_power or 0),
            "day_trade_bp": float(bal.day_trading_buying_power or 0),
            "updated_at": bal.updated_at.isoformat() if bal.updated_at else now_iso,
            "source": "live",
        }
    )
