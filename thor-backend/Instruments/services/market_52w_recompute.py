from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Optional

from django.db import transaction

from Instruments.models.market_24h import MarketTrading24Hour
from Instruments.models.market_52w import Rolling52WeekStats

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Rolling52wRecomputeResult:
    asof_date: date
    window_start: date
    window_days: int
    symbols_seen: int
    updated_rows: int
    skipped_no_data: int


def _normalize_symbols(symbols: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for s in symbols:
        sym = (s or "").strip().upper()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    return out


def recompute_rolling_52w_from_24h(
    *,
    asof_date: date,
    window_days: int = 365,
    symbols: Optional[Iterable[str]] = None,
) -> Rolling52wRecomputeResult:
    """Recompute true rolling 52w highs/lows from 24h daily history.

    This fixes the "expired high/low" problem by rebuilding from the last window.

    Source: MarketTrading24Hour (session_date, high_24h, low_24h)
    Target: Rolling52WeekStats (high_52w/_date, low_52w/_date)

    window_days is inclusive of asof_date.
    """

    if window_days <= 0:
        raise ValueError("window_days must be > 0")

    window_start = asof_date - timedelta(days=window_days - 1)

    if symbols is None:
        symbols_list = list(Rolling52WeekStats.objects.values_list("symbol", flat=True))
        if not symbols_list:
            symbols_list = list(
                MarketTrading24Hour.objects.filter(session_date__gte=window_start, session_date__lte=asof_date)
                .values_list("symbol", flat=True)
                .distinct()
            )
    else:
        symbols_list = list(symbols)

    symbols_norm = _normalize_symbols(symbols_list)

    updated = 0
    skipped = 0

    with transaction.atomic():
        for sym in symbols_norm:
            qs = MarketTrading24Hour.objects.filter(
                symbol=sym,
                session_date__gte=window_start,
                session_date__lte=asof_date,
            )

            max_row = (
                qs.exclude(high_24h__isnull=True)
                .order_by("-high_24h", "session_date")
                .values_list("high_24h", "session_date")
                .first()
            )
            min_row = (
                qs.exclude(low_24h__isnull=True)
                .order_by("low_24h", "session_date")
                .values_list("low_24h", "session_date")
                .first()
            )

            if not max_row or not min_row:
                skipped += 1
                continue

            high_52w, high_date = max_row
            low_52w, low_date = min_row

            if high_52w is None or low_52w is None or high_date is None or low_date is None:
                skipped += 1
                continue

            Rolling52WeekStats.objects.update_or_create(
                symbol=sym,
                defaults={
                    "high_52w": high_52w,
                    "high_52w_date": high_date,
                    "low_52w": low_52w,
                    "low_52w_date": low_date,
                },
            )
            updated += 1

    return Rolling52wRecomputeResult(
        asof_date=asof_date,
        window_start=window_start,
        window_days=window_days,
        symbols_seen=len(symbols_norm),
        updated_rows=updated,
        skipped_no_data=skipped,
    )
