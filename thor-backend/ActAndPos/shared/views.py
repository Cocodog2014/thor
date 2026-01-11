"""Shared cross-domain views.

Views that don't belong to paper or live specifically but serve
both domains or aggregate across them.
"""
from __future__ import annotations

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import NotAuthenticated

from ..paper.models import PaperBalance
from ..live.models import LiveBalance


@api_view(["GET"])
def account_balance_view(request):
    """GET /api/accounts/balance/
    
    Aggregates both paper and live balances for the authenticated user.
    For now, returns the first balance found (paper preferred).
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise NotAuthenticated("Authentication required")
    
    # Try paper first
    paper_bal = PaperBalance.objects.filter(user=user).order_by("account_key").first()
    if paper_bal:
        return Response({
            "broker": "PAPER",
            "account_id": paper_bal.account_key,
            "cash": float(paper_bal.cash),
            "equity": float(paper_bal.equity),
            "net_liq": float(paper_bal.net_liq),
            "buying_power": float(paper_bal.buying_power),
            "updated_at": paper_bal.updated_at.isoformat() if paper_bal.updated_at else None,
        })
    
    # Fall back to live
    live_bal = LiveBalance.objects.filter(user=user).order_by("broker", "broker_account_id").first()
    if live_bal:
        return Response({
            "broker": live_bal.broker,
            "account_id": live_bal.broker_account_id,
            "cash": float(live_bal.cash),
            "equity": float(live_bal.equity),
            "net_liq": float(live_bal.net_liq),
            "buying_power": float(live_bal.stock_buying_power or 0),
            "updated_at": live_bal.updated_at.isoformat() if live_bal.updated_at else None,
        })
    
    return Response({"detail": "No balance found"}, status=404)
