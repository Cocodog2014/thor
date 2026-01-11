from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, Optional

from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ActAndPos.views.accounts import get_active_account

from ActAndPos.live.models import LiveBalance
from ActAndPos.paper.models import PaperBalance

try:  # LiveData redis helper (publishes balances/positions)
    from LiveData.shared.redis_client import live_data_redis
except Exception:  # pragma: no cover - keep endpoint working even if redis helper is unavailable
    live_data_redis = None  # type: ignore


def _as_float(value: Any) -> float:
    try:
        if isinstance(value, Decimal):
            return float(value)
        return float(str(value))
    except Exception:
        return 0.0


def _extract_balance_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize various balance payload shapes into a consistent structure."""

    def pick(*keys: str) -> Optional[Any]:
        for key in keys:
            if key in payload and payload[key] is not None:
                return payload[key]
        return None

    return {
        "net_liquidation": _as_float(pick("net_liq", "net_liquidation", "net_liquidating_value", "account_value", "liquidationValue")),
        "equity": _as_float(pick("equity")),
        "cash": _as_float(pick("cash", "cash_balance", "cashBalance")),
        "buying_power": _as_float(pick("buying_power", "stock_buying_power", "marginBuyingPower", "buyingPower")),
        "day_trade_bp": _as_float(pick("day_trade_bp", "day_trading_buying_power", "dayTradingBuyingPower")),
    }


def _account_identifier(account) -> str:
    """Canonical identifier we surface to clients (prefer the broker hash)."""

    return str(getattr(account, "broker_account_id", None) or getattr(account, "id", ""))


def _read_redis_balance(account) -> Optional[Dict[str, Any]]:
    if live_data_redis is None:
        return None

    client = getattr(live_data_redis, "client", None)
    if client is None:
        return None

    account_identifier = _account_identifier(account)
    candidate_keys: Iterable[str] = (
        f"live_data:balances:{account_identifier}",
        f"live_data:balances:{account.id}",
    )

    for key in candidate_keys:
        try:
            raw = client.get(key)
        except Exception:
            continue

        if not raw:
            continue

        try:
            payload = json.loads(raw)
        except Exception:
            continue

        data = _extract_balance_fields(payload)
        data["account_id"] = account_identifier
        data["source"] = "redis"
        # prefer payload timestamp fields when present
        ts = payload.get("updated_at") or payload.get("timestamp") or payload.get("asof")
        if ts:
            try:
                data["updated_at"] = str(ts)
            except Exception:
                data["updated_at"] = timezone.now().isoformat()
        else:
            data["updated_at"] = timezone.now().isoformat()
        return data

    return None


def _paper_balance(account) -> Dict[str, Any]:
    account_identifier = _account_identifier(account)
    bal = PaperBalance.objects.filter(user=account.user, account_key=str(account.broker_account_id)).first()
    if bal is None:
        return {
            "account_id": account_identifier,
            "net_liquidation": 0.0,
            "equity": 0.0,
            "cash": 0.0,
            "buying_power": 0.0,
            "day_trade_bp": 0.0,
            "source": "paper_db",
            "updated_at": datetime.utcnow().isoformat(),
        }
    return {
        "account_id": account_identifier,
        "net_liquidation": _as_float(bal.net_liq),
        "equity": _as_float(bal.equity),
        "cash": _as_float(bal.cash),
        "buying_power": _as_float(bal.buying_power),
        "day_trade_bp": _as_float(bal.day_trade_bp),
        "source": "paper_db",
        "updated_at": bal.updated_at.isoformat() if bal.updated_at else datetime.utcnow().isoformat(),
    }


def _live_balance(account) -> Dict[str, Any]:
    account_identifier = _account_identifier(account)
    bal = LiveBalance.objects.filter(
        user=account.user,
        broker=str(account.broker),
        broker_account_id=str(account.broker_account_id),
    ).order_by("-updated_at").first()
    if bal is None:
        return {
            "account_id": account_identifier,
            "net_liquidation": 0.0,
            "equity": 0.0,
            "cash": 0.0,
            "buying_power": 0.0,
            "day_trade_bp": 0.0,
            "source": "live_db",
            "updated_at": datetime.utcnow().isoformat(),
        }
    return {
        "account_id": account_identifier,
        "net_liquidation": _as_float(bal.net_liq),
        "equity": _as_float(bal.equity),
        "cash": _as_float(bal.cash),
        "buying_power": _as_float(bal.stock_buying_power),
        "day_trade_bp": _as_float(bal.day_trading_buying_power),
        "source": "live_db",
        "updated_at": bal.updated_at.isoformat() if bal.updated_at else datetime.utcnow().isoformat(),
    }


@api_view(["GET"])
def account_balance_view(request):
    """
    Canonical balance endpoint.

    Order of precedence:
    - SCHWAB/LIVE: Redis live_data:balances:<account_hash> then LiveBalance
    - PAPER: PaperBalance
    """

    account = get_active_account(request)

    if getattr(account, "broker", None) == "PAPER":
        return Response(_paper_balance(account))

    redis_balance = _read_redis_balance(account)
    if redis_balance:
        return Response(redis_balance)

    return Response(_live_balance(account))