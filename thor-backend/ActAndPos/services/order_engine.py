# ActAndPos/services/order_engine.py

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Tuple

from django.db import transaction
from django.utils import timezone

from LiveData.shared.redis_client import live_data_redis

from ..models import Account, Order, Position
from Trades.models import Trade

DecimalLike = Decimal | str | float | int


# --- Errors -----------------------------------------------------------------


class OrderEngineError(Exception):
    """Base error for order-engine problems."""


class InvalidOrderRequest(OrderEngineError):
    """Raised when the request itself is invalid."""


class InsufficientBuyingPower(OrderEngineError):
    """Raised when the account does not have enough BP."""


# --- Generic order params (used for all brokers) -----------------------------


@dataclass
class OrderParams:
    """
    Generic order parameters for ALL brokers managed by Thor.

    We keep this broker-agnostic. The router + adapters decide how to
    interpret these fields for each backend.
    """
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


def _get_live_price_from_redis(symbol: str) -> Decimal | None:
    """Look up the latest quote for symbol from Redis and return a price."""

    quote = live_data_redis.get_latest_quote(symbol.upper())
    if not quote:
        return None

    for field in ("last", "bid", "ask", "close"):
        value = quote.get(field)
        if value in (None, "", "None"):
            continue
        try:
            return Decimal(str(value))
        except Exception:
            continue

    return None


def _evaluate_fill_decision(
    params: OrderParams, live_price: Decimal | None
) -> Tuple[bool, Decimal | None]:
    """
    Determine whether an order should fill immediately and at what price.

    Returns (should_fill_now, fill_price_or_none).
    """

    order_type = params.order_type.upper()
    side = params.side.upper()

    if order_type == "MKT":
        if live_price is None:
            raise InvalidOrderRequest(
                "Cannot fill market order: no live market price available for "
                "this symbol in the order engine. Start the TOS feed or use a "
                "limit order with an explicit price."
            )
        return True, live_price

    if order_type in ("LMT", "STP_LMT"):
        limit_price = params.limit_price
        if limit_price is None:
            raise InvalidOrderRequest("limit_price is required for limit orders.")

        if live_price is None:
            # No market data yet – leave order working.
            return False, None

        if side == "BUY" and live_price <= limit_price:
            return True, limit_price

        if side == "SELL" and live_price >= limit_price:
            return True, limit_price

        return False, None

    raise InvalidOrderRequest(
        f"Unsupported order_type for this engine: {order_type}. "
        "Only MKT and LMT/STP_LMT are supported right now."
    )


def _validate_params(params: OrderParams) -> None:
    """Basic validation that applies to all brokers managed by Thor."""

    if params.quantity <= 0:
        raise InvalidOrderRequest("Quantity must be positive.")

    if params.side not in ("BUY", "SELL"):
        raise InvalidOrderRequest("Side must be BUY or SELL.")

    if params.order_type not in ("MKT", "LMT", "STP", "STP_LMT"):
        raise InvalidOrderRequest("Unsupported order_type for this engine.")

    if params.order_type in ("LMT", "STP_LMT") and params.limit_price is None:
        raise InvalidOrderRequest("limit_price is required for limit orders.")


def place_order(params: OrderParams) -> Tuple[Order, Trade | None, Position | None, Account]:
    """Main entry point for ALL accounts managed inside Thor."""

    return _place_order_internal(params)


# --- INTERNAL ORDER EXECUTION -----------------------------------------------


@transaction.atomic
def _place_order_internal(params: OrderParams) -> Tuple[Order, Trade | None, Position | None, Account]:
    """Execute an order against the internal simulation engine."""

    _validate_params(params)

    account = Account.objects.select_for_update().get(pk=params.account.pk)

    live_price = _get_live_price_from_redis(params.symbol)
    should_fill, fill_price = _evaluate_fill_decision(params, live_price)

    if should_fill and fill_price is None:
        raise InvalidOrderRequest("Unable to determine fill price for this order.")

    if should_fill and params.side.upper() == "BUY":
        notional = fill_price * params.quantity  # type: ignore[arg-type]
        if account.cash < notional:
            raise InsufficientBuyingPower("Insufficient buying power for this order (cash account).")

    now = timezone.now()

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

    if not should_fill:
        return order, None, None, account

    assert fill_price is not None  # for type checkers

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

    order.status = "FILLED"
    order.time_filled = now
    order.time_last_update = now
    order.save(update_fields=["status", "time_filled", "time_last_update"])

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

    if params.side.upper() == "SELL":
        if position.quantity <= 0:
            raise InvalidOrderRequest(
                "Cannot sell: no existing long position (short selling is disabled)."
            )
        if qty > position.quantity:
            raise InvalidOrderRequest(
                "Cannot sell more than current position size (short selling is disabled)."
            )

    if params.side.upper() == "BUY":
        q_old = position.quantity
        q_new = q_old + qty

        if q_old == 0:
            avg_new = fill_price
        else:
            avg_new = (q_old * position.avg_price + qty * fill_price) / q_new

        position.quantity = q_new
        position.avg_price = avg_new
        position.mark_price = fill_price

    else:
        q_old = position.quantity
        q_new = q_old - qty

        realized = (fill_price - position.avg_price) * qty * mult
        position.realized_pl_day += realized
        position.realized_pl_open += realized

        position.quantity = q_new
        position.mark_price = fill_price

    position.save()

    trade_value = fill_price * params.quantity * mult
    total_cost = trade_value + params.commission + params.fees

    if params.side.upper() == "BUY":
        account.cash -= total_cost
    else:
        account.cash += trade_value - (params.commission + params.fees)

    positions = Position.objects.filter(account=account)
    total_market_value = sum((p.market_value for p in positions), Decimal("0"))

    account.net_liq = account.cash + total_market_value

    account.stock_buying_power = account.cash
    account.option_buying_power = account.cash
    account.day_trading_buying_power = account.cash

    account.current_cash = account.cash
    account.equity = account.net_liq

    account.save()

    return order, trade, position, account


