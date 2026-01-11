from __future__ import annotations

from decimal import Decimal

from django.db.models import QuerySet

from ActAndPos.live.models import LiveBalance, LiveExecution, LivePosition
from ActAndPos.shared.statement.dto import (
    StatementBalance,
    StatementDateRange,
    StatementPnlRow,
    StatementPosition,
    StatementSourceData,
    StatementTrade,
)


def _zero_balance() -> StatementBalance:
    return StatementBalance(
        currency="USD",
        net_liq=Decimal("0"),
        cash=Decimal("0"),
        equity=Decimal("0"),
        stock_buying_power=Decimal("0"),
        option_buying_power=Decimal("0"),
        day_trading_buying_power=Decimal("0"),
        updated_at=None,
    )


def build(*, user, broker_account_id: str, date_range: StatementDateRange, broker: str | None = None) -> StatementSourceData:
    """Read-only LIVE statement source.

    Pulls from LiveBalance/LivePosition/LiveExecution.
    """

    balance_qs = LiveBalance.objects.filter(user=user, broker_account_id=broker_account_id)
    if broker:
        balance_qs = balance_qs.filter(broker=broker)
    bal = balance_qs.order_by("-updated_at").first()

    if bal is None:
        balance = _zero_balance()
    else:
        balance = StatementBalance(
            currency=bal.currency or "USD",
            net_liq=bal.net_liq,
            cash=bal.cash,
            equity=bal.equity,
            stock_buying_power=bal.stock_buying_power,
            option_buying_power=bal.option_buying_power,
            day_trading_buying_power=bal.day_trading_buying_power,
            updated_at=bal.updated_at,
        )

    positions_qs: QuerySet[LivePosition] = LivePosition.objects.filter(
        user=user,
        broker_account_id=broker_account_id,
    ).exclude(symbol="")
    if broker:
        positions_qs = positions_qs.filter(broker=broker)
    positions_qs = positions_qs.order_by("symbol")

    positions: list[StatementPosition] = []
    pnl_rows: list[StatementPnlRow] = []

    for p in positions_qs:
        positions.append(
            StatementPosition(
                symbol=p.symbol,
                description=p.description or "",
                qty=p.quantity,
                avg_price=p.avg_price,
                mark_price=p.mark_price,
                multiplier=p.multiplier,
                currency=p.currency or balance.currency,
                broker_payload=p.broker_payload,
            )
        )
        pnl_rows.append(
            StatementPnlRow(
                symbol=p.symbol,
                description=p.description or "",
                pl_open=Decimal("0"),
                pl_pct=Decimal("0"),
                pl_day=p.broker_pl_day,
                pl_ytd=p.broker_pl_ytd,
            )
        )

    exec_qs: QuerySet[LiveExecution] = (
        LiveExecution.objects.filter(
            user=user,
            broker_account_id=broker_account_id,
            exec_time__date__gte=date_range.start,
            exec_time__date__lte=date_range.end,
        )
        .select_related("order")
        .order_by("-exec_time")
    )
    if broker:
        exec_qs = exec_qs.filter(broker=broker)

    trades: list[StatementTrade] = []
    for e in exec_qs:
        trades.append(
            StatementTrade(
                id=str(e.broker_exec_id or e.pk),
                symbol=e.symbol,
                side=e.side,
                quantity=e.quantity,
                price=e.price,
                commission=e.commission,
                fees=e.fees,
                exec_time=e.exec_time,
                order=e.order_id,
            )
        )

    return StatementSourceData(
        balance=balance,
        positions=positions,
        pnl_by_symbol=pnl_rows,
        trades=trades,
    )
