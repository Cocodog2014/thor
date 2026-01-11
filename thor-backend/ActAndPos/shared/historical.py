from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol, Sequence


class Timeframe(str, Enum):
    MIN_1 = "1m"
    MIN_5 = "5m"
    MIN_15 = "15m"
    HOUR_1 = "1h"
    DAY_1 = "1d"


@dataclass(frozen=True)
class Bar:
    ts: datetime
    o: Decimal
    h: Decimal
    l: Decimal
    c: Decimal
    v: Decimal | None = None


class HistoricalDataSource(Protocol):
    """Contract for historical data retrieval.

    Implementations live outside `shared` (e.g., in live/brokers/*).
    PAPER must be able to depend on this interface without importing broker code.
    """

    def get_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> Sequence[Bar]:
        raise NotImplementedError
