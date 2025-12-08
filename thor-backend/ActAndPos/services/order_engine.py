# ActAndPos/services/order_engine.py

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Tuple, Protocol

from django.db import transaction
from django.utils import timezone

from ..models import Account, Order, Position
from Trades.models import Trade

DecimalLike = Decimal | str | float | int


# --- Errors (still mainly used by PAPER path for now) ------------------------


class PaperTradingError(Exception):
    """Base error for paper trading problems."""


class InvalidPaperOrder(PaperTradingError):
    """Raised when the request itself is invalid."""


class InsufficientBuyingPower(PaperTradingError):
    """Raised when the account does not have enough BP."""


# --- Generic order params (used for all brokers) -----------------------------


@dataclass
class OrderParams:
    """
    Generic order parameters for ALL brokers (PAPER, SCHWAB, etc.).

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


def _get_fill_price(params: OrderParams) -> Decimal:
    """
    Simple v1 logic (PAPER only for now):

    - If a limit price is provided, use that.
    - Otherwise, pretend the current market price is 100.
      (Later we can plug in real quotes here for PAPER too.)
    """
    if params.limit_price is not None:
        return params.limit_price
    return Decimal("100")


def _validate_params(params: OrderParams) -> None:
    """
    Validation for PAPER orders.

    The router ensures only PAPER accounts hit the PAPER path, but we
    keep this check as a safety net.
    """
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


class BrokerAdapter(Protocol):
        """Common interface for all broker adapters (paper, Schwab, etc.)."""

        def place_order(self, params: OrderParams) -> Tuple[Order, Trade, Position, Account]:
                ...


class PaperBrokerAdapter:
    """Adapter that runs the internal PAPER simulation logic."""

    def place_order(self, params: OrderParams) -> Tuple[Order, Trade, Position, Account]:
        # delegate to the paper implementation below
        return _place_order_paper(params)


class SchwabBrokerAdapter:
    """Stub adapter for SCHWAB broker until real API wiring exists."""

    def place_order(self, params: OrderParams) -> Tuple[Order, Trade, Position, Account]:
        return _place_order_schwab(params)


def _get_adapter_for_account(account: Account) -> BrokerAdapter:
    """Pick the correct adapter based on account.broker."""

    if account.broker == "PAPER":
        return PaperBrokerAdapter()
    if account.broker == "SCHWAB":
        return SchwabBrokerAdapter()
    raise ValueError(f"Unsupported broker: {account.broker!r}")


# --- Public entry point: ORDER ROUTER ----------------------------------------


def place_order(params: OrderParams) -> Tuple[Order, Trade, Position, Account]:
    """
    Main entry point for ALL orders (paper, Schwab, etc.).

    The rest of the app should call THIS function.

    It picks the correct adapter (Paper, Schwab, etc.) and delegates
    to the broker-specific implementation.
    """
    adapter = _get_adapter_for_account(params.account)
    return adapter.place_order(params)


# --- PAPER implementation (moved from old place_paper_order) -----------------


@transaction.atomic
def _place_order_paper(params: OrderParams) -> Tuple[Order, Trade, Position, Account]:
    """
    PAPER broker implementation:
    - create a PAPER Order
    - immediately fill it
    - update Position & Account
    - return all four objects
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
    positions = Position.objects.filter(account=account)
    total_market_value = sum((p.market_value for p in positions), Decimal("0"))

    account.net_liq = account.cash + total_market_value

    # Simple v1 BP rules
    factor_equity = Decimal("4")
    factor_options = Decimal("2")

    account.stock_buying_power = account.net_liq * factor_equity
    account.option_buying_power = account.net_liq * factor_options
    account.day_trading_buying_power = account.net_liq * factor_equity

    account.current_cash = account.cash
    account.equity = account.net_liq

    account.save()

    return order, trade, position, account


# --- SCHWAB stub implementation ----------------------------------------------


def _place_order_schwab(params: OrderParams) -> Tuple[Order, Trade, Position, Account]:
    """
    SCHWAB broker implementation (STUB).

    This is here so the *shape* of the logic is ready. When you hook up
    the real Schwab API, you'll implement the steps inside this function.

    IMPORTANT: For now this ALWAYS raises NotImplementedError, so you
    won't accidentally think Schwab trading is live.
    """

    account = params.account
    if account.broker != "SCHWAB":
        # Safety net – this path should only run for Schwab accounts.
        raise ValueError(
            f"_place_order_schwab called for non-Schwab account: {account.broker!r}"
        )

    # --- FUTURE IMPLEMENTATION PLAN (when Schwab API is wired in) -------------
    #
    # 1) Build Schwab API order payload from OrderParams:
    #       - symbol
    #       - side (BUY/SELL)
    #       - quantity
    #       - order_type (MKT/LMT/STP/STP_LMT)
    #       - limit/stop prices if present
    #
    # 2) Send order to Schwab via REST/SDK.
    #       - Capture Schwab's order ID: broker_order_id
    #
    # 3) Create a local Order row with:
    #       status = "WORKING" or "PENDING"
    #       broker_order_id = <value from Schwab>
    #       time_placed = now
    #
    # 4) DO NOT create a Trade or update Position yet.
    #       - Fills will come back asynchronously:
    #           - via polling a Schwab endpoint, or
    #           - a callback/webhook if available.
    #
    # 5) In a separate sync task:
    #       - Fetch fills for broker_order_id
    #       - Create Trade rows
    #       - Update Position & Account (similar to PAPER logic)
    #
    # 6) Return a tuple of objects once implementation is ready.
    #
    # Until all that exists, we raise NotImplementedError.

    raise NotImplementedError(
        "Schwab order path is stubbed. Implement _place_order_schwab() "
        "once the Schwab API client is available."
    )
