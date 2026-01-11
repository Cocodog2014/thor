from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class StatementDateRange:
    start: date
    end: date


@dataclass(frozen=True)
class StatementBalance:
    currency: str
    net_liq: Decimal
    cash: Decimal
    equity: Decimal
    stock_buying_power: Decimal
    option_buying_power: Decimal
    day_trading_buying_power: Decimal
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class StatementPosition:
    symbol: str
    description: str
    qty: Decimal
    avg_price: Decimal
    mark_price: Decimal
    multiplier: Decimal
    currency: str
    broker_payload: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class StatementPnlRow:
    symbol: str
    description: str
    pl_open: Decimal
    pl_pct: Decimal
    pl_day: Decimal
    pl_ytd: Decimal


@dataclass(frozen=True)
class StatementTrade:
    id: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    commission: Decimal
    fees: Decimal
    exec_time: datetime
    order: Optional[int] = None


@dataclass(frozen=True)
class StatementSourceData:
    balance: StatementBalance
    positions: List[StatementPosition]
    pnl_by_symbol: List[StatementPnlRow]
    trades: List[StatementTrade]
