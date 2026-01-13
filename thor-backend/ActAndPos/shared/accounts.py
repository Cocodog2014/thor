"""Shared account resolution and serialization helpers.

Used by both paper and live domains and cross-domain endpoints like
activity_today, account_summary, positions, balances.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

from rest_framework.exceptions import NotAuthenticated

from ..live.models import LiveBalance
from ..paper.models import PaperBalance
from ..serializers import AccountSummarySerializer


PAPER_DEFAULT_BALANCE = Decimal("100000.00")


@dataclass(frozen=True)
class ActiveAccount:
    """Lightweight account reference combining paper and live domains."""

    user: Any
    broker: str
    broker_account_id: str
    display_name: str = ""
    account_number: str | None = None
    currency: str = "USD"

    @property
    def id(self) -> str:
        return str(self.broker_account_id)


def _as_money_str(value) -> str:
    if value is None:
        return "0.00"
    return str(value)


def _has_any_paper_balance(user) -> bool:
    return PaperBalance.objects.filter(user=user, account_key__istartswith="PAPER-").exists()


def _ensure_default_paper_balance(user) -> PaperBalance:
    """Guarantee every user has at least one PaperBalance."""
    existing = PaperBalance.objects.filter(user=user, account_key__istartswith="PAPER-").order_by("account_key").first()
    if existing is not None:
        return existing

    account_key = f"PAPER-{getattr(user, 'pk', 'NOUSER')}"
    bal, _ = PaperBalance.objects.get_or_create(
        user=user,
        account_key=account_key,
        defaults={
            "currency": "USD",
            "cash": PAPER_DEFAULT_BALANCE,
            "equity": PAPER_DEFAULT_BALANCE,
            "net_liq": PAPER_DEFAULT_BALANCE,
            "buying_power": PAPER_DEFAULT_BALANCE,
            "day_trade_bp": PAPER_DEFAULT_BALANCE,
        },
    )
    return bal


def ensure_default_paper_balance(user) -> PaperBalance:
    """Public wrapper to guarantee a default paper balance exists."""
    return _ensure_default_paper_balance(user)


def _extract_schwab_account_number(payload: dict | None) -> str | None:
    if not payload or not isinstance(payload, dict):
        return None
    sec = payload.get("securitiesAccount")
    if isinstance(sec, dict):
        num = sec.get("accountNumber")
        return str(num) if num else None
    return None


def _extract_schwab_display_name(payload: dict | None) -> str | None:
    if not payload or not isinstance(payload, dict):
        return None
    sec = payload.get("securitiesAccount")
    if isinstance(sec, dict):
        for k in ("displayName", "nickname", "accountNumber"):
            val = sec.get(k)
            if val:
                return str(val)
    for k in ("displayName", "nickname"):
        val = payload.get(k)
        if val:
            return str(val)
    return None


def _account_summary_for_paper(*, user, bal: PaperBalance) -> ActiveAccount:
    account_key = str(bal.account_key)
    return ActiveAccount(
        user=user,
        broker="PAPER",
        broker_account_id=account_key,
        display_name=f"Paper Trading ({account_key})",
        account_number=None,
        currency=bal.currency or "USD",
    )


def _account_summary_for_live(*, user, bal: LiveBalance) -> ActiveAccount:
    acct_num = _extract_schwab_account_number(bal.broker_payload)
    display = _extract_schwab_display_name(bal.broker_payload) or str(bal.broker_account_id)
    return ActiveAccount(
        user=user,
        broker=str(bal.broker or "SCHWAB").upper(),
        broker_account_id=str(bal.broker_account_id),
        display_name=display,
        account_number=acct_num,
        currency=bal.currency or "USD",
    )


def iter_accounts_for_user(user) -> Iterable[ActiveAccount]:
    """Yield all accounts (paper + live) for a user."""
    # Live accounts from balances
    for bal in LiveBalance.objects.filter(user=user).order_by("broker", "broker_account_id"):
        yield _account_summary_for_live(user=user, bal=bal)

    # Paper accounts from balances
    for bal in PaperBalance.objects.filter(user=user, account_key__istartswith="PAPER-").order_by("account_key"):
        yield _account_summary_for_paper(user=user, bal=bal)


def serialize_account(account: ActiveAccount) -> dict:
    """Serialize an ActiveAccount to JSON with balance fields."""
    if account.broker == "PAPER":
        bal = PaperBalance.objects.filter(user=account.user, account_key=str(account.broker_account_id)).first()
        if bal is None:
            bal = _ensure_default_paper_balance(account.user)

        net_liq = bal.net_liq
        cash = bal.cash
        equity = bal.equity
        stock_bp = bal.buying_power
        option_bp = bal.buying_power
        dt_bp = bal.day_trade_bp
        ok_to_trade = bool(net_liq > 0 and dt_bp > 0)

        return {
            "id": account.id,
            "broker": account.broker,
            "broker_account_id": account.broker_account_id,
            "account_number": None,
            "display_name": account.display_name or str(account.broker_account_id),
            "currency": account.currency or "USD",
            "net_liq": _as_money_str(net_liq),
            "cash": _as_money_str(cash),
            "starting_balance": _as_money_str(net_liq),
            "current_cash": _as_money_str(cash),
            "equity": _as_money_str(equity),
            "stock_buying_power": _as_money_str(stock_bp),
            "option_buying_power": _as_money_str(option_bp),
            "day_trading_buying_power": _as_money_str(dt_bp),
            "ok_to_trade": ok_to_trade,
        }

    bal = LiveBalance.objects.filter(
        user=account.user,
        broker=str(account.broker or "SCHWAB").upper(),
        broker_account_id=str(account.broker_account_id),
    ).order_by("-updated_at").first()

    if bal is None:
        ok_to_trade = False
        return {
            "id": account.id,
            "broker": account.broker,
            "broker_account_id": account.broker_account_id,
            "account_number": account.account_number,
            "display_name": account.display_name or str(account.broker_account_id),
            "currency": account.currency or "USD",
            "net_liq": "0.00",
            "cash": "0.00",
            "starting_balance": "0.00",
            "current_cash": "0.00",
            "equity": "0.00",
            "stock_buying_power": "0.00",
            "option_buying_power": "0.00",
            "day_trading_buying_power": "0.00",
            "ok_to_trade": ok_to_trade,
        }

    ok_to_trade = bool(bal.net_liq > 0 and bal.day_trading_buying_power > 0)
    return {
        "id": account.id,
        "broker": account.broker,
        "broker_account_id": account.broker_account_id,
        "account_number": account.account_number,
        "display_name": account.display_name or str(account.broker_account_id),
        "currency": account.currency or "USD",
        "net_liq": _as_money_str(bal.net_liq),
        "cash": _as_money_str(bal.cash),
        "starting_balance": _as_money_str(bal.net_liq),
        "current_cash": _as_money_str(bal.cash),
        "equity": _as_money_str(bal.equity),
        "stock_buying_power": _as_money_str(bal.stock_buying_power),
        "option_buying_power": _as_money_str(bal.option_buying_power),
        "day_trading_buying_power": _as_money_str(bal.day_trading_buying_power),
        "ok_to_trade": ok_to_trade,
    }


def get_active_account(request) -> ActiveAccount:
    """Resolve account from request (query param or default)."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise NotAuthenticated("Authentication required to access trading accounts.")

    params = getattr(request, "query_params", None) or getattr(request, "GET", {})
    account_id = params.get("account_id")

    try:
        return resolve_account_for_user(user=user, account_id=account_id)
    except ValueError:
        # If the UI has a stale selection (e.g., legacy/test paper keys),
        # fall back to the default account instead of 500'ing.
        return resolve_account_for_user(user=user, account_id=None)


def resolve_account_for_user(*, user, account_id: str | None) -> ActiveAccount:
    """Resolve account by ID or return default."""
    if not _has_any_paper_balance(user):
        _ensure_default_paper_balance(user)

    accounts = list(iter_accounts_for_user(user))
    if account_id:
        wanted = str(account_id)
        for acct in accounts:
            if str(acct.id) == wanted or str(acct.broker_account_id) == wanted:
                return acct
        raise ValueError("Account not found.")

    # Prefer SCHWAB, fallback to first
    for acct in accounts:
        if str(acct.broker).upper() == "SCHWAB":
            return acct

    return accounts[0]


def serialize_active_account(*, request, account: ActiveAccount) -> dict:
    """Serialize account with serializer context."""
    payload = serialize_account(account)
    return AccountSummarySerializer(payload, context={"user": request.user}).data
