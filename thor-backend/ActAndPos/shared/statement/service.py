from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Tuple

from django.utils import timezone

from ActAndPos.shared.formatting import format_money, format_pct
from ActAndPos.shared.marketdata import get_marks
from ActAndPos.shared.statement.dto import (
    StatementDateRange,
    StatementPnlRow,
    StatementPosition,
    StatementSourceData,
)


MAX_RANGE_DAYS = 370


def _resolve_date_range(
    today: date,
    days_back_param: str | None,
    from_param: str | None,
    to_param: str | None,
) -> Tuple[date, date]:
    if days_back_param and not (from_param or to_param):
        try:
            days_back = int(days_back_param)
        except ValueError as exc:
            raise ValueError("days_back must be an integer.") from exc
        days_back = max(1, min(days_back, MAX_RANGE_DAYS))
        start = today - timedelta(days=days_back - 1)
        return start, today

    if from_param or to_param:
        if not (from_param and to_param):
            raise ValueError("Both from and to parameters are required.")

        start = date.fromisoformat(from_param)
        end = date.fromisoformat(to_param)

        if start > end:
            start, end = end, start

        if (end - start).days >= MAX_RANGE_DAYS:
            start = end - timedelta(days=MAX_RANGE_DAYS - 1)

        return start, end

    return today, today


def _row_id(prefix: str, symbol: str) -> str:
    return f"{prefix}-{symbol.upper()}"


def _format_qty(qty: Decimal) -> str:
    """Human-friendly qty string without forcing 2dp."""

    try:
        if qty % 1 == 0:
            return str(qty.quantize(Decimal("1")))
        # Keep up to 4 decimals (matches model precision) and trim zeros.
        return f"{qty.quantize(Decimal('0.0001')).normalize():f}"
    except Exception:
        return str(qty)


def _build_summary_rows(balance) -> List[Dict[str, str]]:
    return [
        {"id": "net_liq", "metric": "Net Liquidating Value", "value": format_money(balance.net_liq)},
        {"id": "cash", "metric": "Cash", "value": format_money(balance.cash)},
        {"id": "stock_bp", "metric": "Stock Buying Power", "value": format_money(balance.stock_buying_power)},
        {"id": "option_bp", "metric": "Option Buying Power", "value": format_money(balance.option_buying_power)},
        {"id": "dt_bp", "metric": "Day Trading Buying Power", "value": format_money(balance.day_trading_buying_power)},
        {"id": "equity", "metric": "Equity", "value": format_money(balance.equity)},
    ]


def build_statement(*, user, account, days_back: str | None, from_param: str | None, to_param: str | None) -> Dict[str, Any]:
    """Build the AccountStatement payload (same shape for PAPER or LIVE).

    Output shape matches the current React page in
    `thor-frontend/src/pages/AccountStatement/AccountStatement.tsx`.
    """

    today = timezone.localdate()
    start_date, end_date = _resolve_date_range(today, days_back, from_param, to_param)

    if str(getattr(account, "broker", "")).upper() == "PAPER":
        from ActAndPos.paper.statement_source import build as build_source

        source: StatementSourceData = build_source(
            user=user,
            account_key=str(getattr(account, "broker_account_id", "")),
            date_range=StatementDateRange(start=start_date, end=end_date),
        )
    else:
        from ActAndPos.live.statement_source import build as build_source

        source = build_source(
            user=user,
            broker=str(getattr(account, "broker", "SCHWAB")),
            broker_account_id=str(getattr(account, "broker_account_id", "")),
            date_range=StatementDateRange(start=start_date, end=end_date),
        )

    # Overlay marks/quotes (shared)
    symbols = [p.symbol for p in source.positions]
    marks = get_marks(symbols)

    positions: List[StatementPosition] = []
    pnl_rows: List[StatementPnlRow] = []

    for pos, pnl in zip(source.positions, source.pnl_by_symbol, strict=False):
        sym = (pos.symbol or "").upper()
        mark = marks.get(sym)
        mark_price = mark if mark is not None else pos.mark_price

        qty = pos.qty
        mult = pos.multiplier or Decimal("1")
        market_value = qty * mark_price * mult
        cost_basis = qty * pos.avg_price * mult
        pl_open = market_value - cost_basis
        pl_pct = Decimal("0")
        if cost_basis:
            try:
                pl_pct = (pl_open / abs(cost_basis)) * Decimal("100")
            except Exception:
                pl_pct = Decimal("0")

        positions.append(
            StatementPosition(
                symbol=pos.symbol,
                description=pos.description,
                qty=qty,
                avg_price=pos.avg_price,
                mark_price=mark_price,
                multiplier=mult,
                currency=pos.currency,
                broker_payload=pos.broker_payload,
            )
        )

        pnl_rows.append(
            StatementPnlRow(
                symbol=pos.symbol,
                description=pos.description,
                pl_open=pl_open,
                pl_pct=pl_pct,
                pl_day=pnl.pl_day,
                pl_ytd=pnl.pl_ytd,
            )
        )

    equities_rows = [
        {
            "id": _row_id("pos", p.symbol),
            "symbol": p.symbol,
            "description": p.description or "",
            "qty": _format_qty(p.qty),
            "tradePrice": format_money(p.avg_price),
            "mark": format_money(p.mark_price),
            "markValue": format_money(p.qty * p.mark_price * p.multiplier),
        }
        for p in positions
    ]

    pnl_by_symbol_rows = [
        {
            "id": _row_id("pnl", r.symbol),
            "symbol": r.symbol,
            "description": r.description or "",
            "plOpen": format_money(r.pl_open),
            "plPct": format_pct(r.pl_pct),
            "plDay": format_money(r.pl_day),
            "plYtd": format_money(r.pl_ytd),
        }
        for r in pnl_rows
    ]

    trades_rows: List[Dict[str, Any]] = []
    for t in source.trades:
        trades_rows.append(
            {
                "id": t.id,
                "symbol": t.symbol,
                "side": t.side,
                "quantity": str(t.quantity),
                "price": str(t.price),
                "commission": str(t.commission),
                "fees": str(t.fees),
                "exec_time": t.exec_time.isoformat(),
                "order": t.order,
            }
        )

    broker = str(getattr(account, "broker", "SCHWAB")).upper()
    broker_account_id = str(getattr(account, "broker_account_id", ""))
    display_name = getattr(account, "display_name", None) or broker_account_id

    account_payload = {
        "id": getattr(account, "id", broker_account_id),
        "broker": broker,
        "broker_account_id": broker_account_id,
        "account_number": getattr(account, "account_number", None),
        "display_name": display_name,
        "currency": getattr(account, "currency", "USD") or "USD",
        "net_liq": format_money(source.balance.net_liq),
        "cash": format_money(source.balance.cash),
        "stock_buying_power": format_money(source.balance.stock_buying_power),
        "option_buying_power": format_money(source.balance.option_buying_power),
        "day_trading_buying_power": format_money(source.balance.day_trading_buying_power),
        "ok_to_trade": bool(source.balance.net_liq > 0 and source.balance.day_trading_buying_power > 0),
    }

    return {
        "account": account_payload,
        "date_range": {"from": start_date.isoformat(), "to": end_date.isoformat()},
        "cashSweep": [],
        "futuresCash": [],
        "equities": equities_rows,
        "pnlBySymbol": pnl_by_symbol_rows,
        "trades": trades_rows,
        "summary": _build_summary_rows(source.balance),
    }
