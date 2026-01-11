from __future__ import annotations

from decimal import Decimal

from django.db.models import QuerySet

from ActAndPos.paper.models import PaperBalance, PaperFill, PaperPosition
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


def build(*, user, account_key: str, date_range: StatementDateRange) -> StatementSourceData:
    """Read-only PAPER statement source.

    Returns normalized statement data for `account_key` and `date_range`.
    """

    bal = PaperBalance.objects.filter(user=user, account_key=account_key).first()
    if bal is None:
        balance = _zero_balance()
    else:
        balance = StatementBalance(
            currency=bal.currency or "USD",
            net_liq=bal.net_liq,
            cash=bal.cash,
            equity=bal.equity,
            stock_buying_power=bal.buying_power,
            option_buying_power=bal.buying_power,
            day_trading_buying_power=bal.day_trade_bp,
            updated_at=bal.updated_at,
        )

    positions_qs: QuerySet[PaperPosition] = (
        PaperPosition.objects.filter(user=user, account_key=account_key)
        .exclude(symbol="")
        .order_by("symbol")
    )

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
                broker_payload=None,
            )
        )
        pnl_rows.append(
            StatementPnlRow(
                symbol=p.symbol,
                description=p.description or "",
                pl_open=Decimal("0"),
                pl_pct=Decimal("0"),
                pl_day=p.realized_pl_day,
                pl_ytd=p.realized_pl_total,
            )
        )

    fills_qs: QuerySet[PaperFill] = (
        PaperFill.objects.filter(
            user=user,
            account_key=account_key,
            exec_time__date__gte=date_range.start,
            exec_time__date__lte=date_range.end,
        )
        .select_related("order")
        .order_by("-exec_time")
    )

    trades: list[StatementTrade] = []
    for f in fills_qs:
        trades.append(
            StatementTrade(
                id=str(f.exec_id or f.pk),
                symbol=f.symbol,
                side=f.side,
                quantity=f.quantity,
                price=f.price,
                commission=f.commission,
                fees=f.fees,
                exec_time=f.exec_time,
                order=f.order_id,
            )
        )

    return StatementSourceData(
        balance=balance,
        positions=positions,
        pnl_by_symbol=pnl_rows,
        trades=trades,
    )
