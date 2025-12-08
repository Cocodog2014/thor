# ActAndPos/services/paper_engine.py

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Tuple

from django.db import transaction
from django.utils import timezone

from ..models import Account, Order, Position
from Trades.models import Trade


DecimalLike = Decimal | str | float | int


class PaperTradingError(Exception):
    """Base error for paper trading problems."""


class InvalidPaperOrder(PaperTradingError):
    """Raised when the request itself is invalid."""


class InsufficientBuyingPower(PaperTradingError):
    """Raised when the account does not have enough BP."""


@dataclass
class PaperOrderParams:
    account: Account
    symbol: str
    asset_type: str
    side: str
    quantity: Decimal
    order_type: str
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    commission: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")


def _to_decimal(val: DecimalLike | None) -> Decimal | None:
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _get_fill_price(params: PaperOrderParams) -> Decimal:
    """
    Simple v1 logic:
    - If a limit price is provided, use that.
    - Otherwise, pretend the current market price is 100.
      (Later we can plug in real quotes here.)
    """
    if params.limit_price is not None:
        return params.limit_price
    return Decimal("100")


def _validate_params(params: PaperOrderParams) -> None:
    if params.account.broker != "PAPER":
        raise InvalidPaperOrder("Account is not a PAPER trading account.")

    if params.quantity <= 0:
        raise InvalidPaperOrder("Quantity must be positive.")

    if params.side not in ("BUY", "SELL"):
        raise InvalidPaperOrder("Side must be BUY or SELL.")

    if params.order_type not in ("MKT", "LMT", "STP", "STP_LMT"):
        raise InvalidPaperOrder("Unsupported order_type for paper trading.")

    if params.order_type in ("LMT", "STP_LMT") and params.limit_price is None:
        raise InvalidPaperOrder("limit_price is required for limit orders.")


@transaction.atomic
def place_paper_order(params: PaperOrderParams) -> Tuple[Order, Trade, Position, Account]:
    """
    Main entry point: create a PAPER Order, immediately fill it,
    update Position & Account, and return all four objects.
    """

    _validate_params(params)

    # Lock account row – avoid race conditions if we ever do concurrency.
    account = Account.objects.select_for_update().get(pk=params.account.pk)

    fill_price = _get_fill_price(params)

    # Simple BP check: estimated notional vs day-trading BP.
    notional = fill_price * params.quantity
    if params.side == "BUY" and account.day_trading_buying_power < notional:
        raise InsufficientBuyingPower("Insufficient buying power for this order.")

    now = timezone.now()

    # 1) Create the WORKING order
    order = Order.objects.create(
        account=account,
        symbol=params.symbol,
        asset_type=params.asset_type,
        side=params.side,
        quantity=params.quantity,
        order_type=params.order_type,
        limit_price=params.limit_price,
        stop_price=params.stop_price,
        status="WORKING",
        time_placed=now,
    )

    # 2) Create the Trade (fill)
    trade = Trade.objects.create(
        account=account,
        order=order,
        symbol=params.symbol,
        side=params.side,
        quantity=params.quantity,
        price=fill_price,
        commission=params.commission,
        fees=params.fees,
        exec_time=now,
    )

    # Mark order filled
    order.status = "FILLED"
    order.time_filled = now
    order.time_last_update = now
    order.save(update_fields=["status", "time_filled", "time_last_update"])

    # 3) Update (or create) Position
    position, _created = Position.objects.select_for_update().get_or_create(
        account=account,
        symbol=params.symbol,
        asset_type=params.asset_type,
        defaults={
            "description": "",
            "quantity": Decimal("0"),
            "avg_price": fill_price,
            "mark_price": fill_price,
            "multiplier": Decimal("1"),
        },
    )

    qty = params.quantity
    mult = position.multiplier or Decimal("1")

    if params.side == "BUY":
        q_old = position.quantity
        q_new = q_old + qty

        if q_old == 0:
            avg_new = fill_price
        else:
            avg_new = (q_old * position.avg_price + qty * fill_price) / q_new

        position.quantity = q_new
        position.avg_price = avg_new
        position.mark_price = fill_price

    else:  # SELL
        q_old = position.quantity
        q_new = q_old - qty

        # Realized P&L on this leg
        realized = (fill_price - position.avg_price) * qty * mult
        position.realized_pl_day += realized
        position.realized_pl_open += realized

        position.quantity = q_new
        position.mark_price = fill_price

    position.save()

        # 4) Update Account cash & buying power
    trade_value = fill_price * params.quantity * mult
    total_cost = trade_value + params.commission + params.fees

    if params.side == "BUY":
        account.cash -= total_cost
    else:
        account.cash += trade_value - (params.commission + params.fees)

    # Recompute net liq from cash + market value of all positions
    from decimal import Decimal as _D
    from ..models import Position as _Pos

    positions = _Pos.objects.filter(account=account)
    total_market_value = sum((p.market_value for p in positions), _D("0"))

    account.net_liq = account.cash + total_market_value

    # Simple v1 BP rules
    factor_equity = _D("4")
    factor_options = _D("2")

    account.stock_buying_power = account.net_liq * factor_equity
    account.option_buying_power = account.net_liq * factor_options
    account.day_trading_buying_power = account.net_liq * factor_equity

    account.current_cash = account.cash
    account.equity = account.net_liq

    account.save()

    return order, trade, position, account
