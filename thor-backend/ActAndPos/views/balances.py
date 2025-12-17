from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, Optional

from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ActAndPos.models import Account
from ActAndPos.models.snapshots import AccountDailySnapshot
from ActAndPos.views.accounts import get_active_account

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


def _read_redis_balance(account: Account) -> Optional[Dict[str, Any]]:
    if live_data_redis is None:
        return None

    client = getattr(live_data_redis, "client", None)
    if client is None:
        return None

    candidate_keys: Iterable[str] = (
        f"live_data:balances:{account.id}",
        f"live_data:balances:{account.broker_account_id}",
        f"live_data:balances:{account.user_id}:{account.broker_account_id}",
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
        data["account_id"] = str(account.id)
        data["source"] = f"redis:{key}"
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


def _snapshot_balance(account: Account) -> Optional[Dict[str, Any]]:
    snapshot = (
        AccountDailySnapshot.objects.filter(account=account)
        .order_by("-trading_date", "-captured_at")
        .first()
    )
    if snapshot is None:
        return None

    data = {
        "account_id": str(account.id),
        "net_liquidation": _as_float(snapshot.net_liq),
        "equity": _as_float(snapshot.equity),
        "cash": _as_float(snapshot.cash),
        "buying_power": _as_float(snapshot.stock_buying_power),
        "day_trade_bp": _as_float(snapshot.day_trading_buying_power),
        "source": "db:snapshot",
        "updated_at": snapshot.captured_at.isoformat() if snapshot.captured_at else timezone.now().isoformat(),
    }
    return data


def _account_balance(account: Account) -> Dict[str, Any]:
    return {
        "account_id": str(account.id),
        "net_liquidation": _as_float(account.net_liq),
        "equity": _as_float(account.equity),
        "cash": _as_float(account.cash),
        "buying_power": _as_float(account.stock_buying_power),
        "day_trade_bp": _as_float(account.day_trading_buying_power),
        "source": "db:account",
        "updated_at": datetime.utcnow().isoformat(),
    }


@api_view(["GET"])
def account_balance_view(request):
    """
    Canonical balance endpoint.

    Order of precedence:
    1) Redis live_data:balances:<account_id or broker_account_id>
    2) Latest AccountDailySnapshot (EOD/last capture)
    3) Account row values
    """

    account = get_active_account(request)

    # Redis first (live)
    redis_balance = _read_redis_balance(account)
    if redis_balance:
        return Response(redis_balance)

    # Snapshot fallback (most recent captured)
    snapshot_balance = _snapshot_balance(account)
    if snapshot_balance:
        return Response(snapshot_balance)

    # Direct account values as last resort
    return Response(_account_balance(account))