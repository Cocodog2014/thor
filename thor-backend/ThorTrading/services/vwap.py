"""VWAP calculation service.

This module provides a lightweight VWAP service operating on the
`VwapMinute` snapshot table. The snapshot rows store cumulative volume
and last trade price once per symbol per minute. VWAP is derived by
reconstructing *incremental* per‑minute volume as the difference between
successive cumulative_volume values.

VWAP FORMULA (standard):
    VWAP = sum(price_i * volume_i) / sum(volume_i)

Where volume_i is the incremental volume for interval i. Given our
storage of cumulative volumes, we compute:
    incremental_volume_i = cumulative_volume_i - cumulative_volume_{i-1}

Rows with missing data or non‑positive incremental volume are skipped.
If no valid incremental volume exists in the requested range we return
None.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from django.utils import timezone
from django.db import transaction
from django.db.models import QuerySet
from decimal import Decimal

from ThorTrading.models.vwap import VwapMinute


@dataclass
class VwapResult:
    symbol: str
    start: Optional[timezone.datetime]
    end: Optional[timezone.datetime]
    numerator: Decimal
    denominator: Decimal

    @property
    def vwap(self) -> Optional[Decimal]:
        if self.denominator and self.denominator > 0:
            return (self.numerator / self.denominator).quantize(Decimal('0.0001'))
        return None


class VwapService:
    """Service encapsulating VWAP calculations over VwapMinute rows."""

    def _fetch_rows(self, symbol: str, start=None, end=None) -> QuerySet[VwapMinute]:
        qs = VwapMinute.objects.filter(symbol=symbol).order_by('timestamp_minute')
        if start is not None:
            qs = qs.filter(timestamp_minute__gte=start)
        if end is not None:
            qs = qs.filter(timestamp_minute__lte=end)
        return qs

    def calculate_vwap(self, symbol: str, start=None, end=None) -> VwapResult:
        """Calculate VWAP for a symbol within optional time bounds.

        Args:
            symbol: Futures symbol.
            start: Inclusive lower bound (UTC) or None for earliest.
            end: Inclusive upper bound (UTC) or None for latest.
        Returns:
            VwapResult containing numerator, denominator and vwap property.
        """
        rows = list(self._fetch_rows(symbol, start, end))
        numerator = Decimal('0')
        denominator = Decimal('0')

        prev_cum = None
        for r in rows:
            price = r.last_price
            cum = r.cumulative_volume
            if price is None or cum is None:
                prev_cum = cum
                continue
            if prev_cum is None:
                # First row in range: treat cumulative as incremental
                inc = cum
                prev_cum = cum
            else:
                inc = cum - prev_cum
                prev_cum = cum
            if inc is None or inc <= 0:
                continue
            inc_dec = Decimal(str(inc))
            numerator += (price * inc_dec)
            denominator += inc_dec

        return VwapResult(
            symbol=symbol,
            start=start,
            end=end,
            numerator=numerator,
            denominator=denominator,
        )

    def get_today_vwap(self, symbol: str) -> Optional[Decimal]:
        tz_now = timezone.now()
        start = tz_now.replace(hour=0, minute=0, second=0, microsecond=0)
        res = self.calculate_vwap(symbol, start=start, end=tz_now)
        return res.vwap

    def calculate_rolling_vwap(self, symbol: str, lookback_minutes: int, now_dt=None) -> Optional[Decimal]:
        """Calculate VWAP over the last `lookback_minutes` minutes ending at `now_dt`.

        Uses the previous cumulative volume just BEFORE the window start to derive
        the correct incremental volume for the first in-window row.
        """
        if lookback_minutes <= 0:
            return None
        if now_dt is None:
            now_dt = timezone.now().replace(second=0, microsecond=0)
        start = now_dt - timezone.timedelta(minutes=lookback_minutes)
        # Previous row outside window (highest timestamp < start)
        prev_row = (
            VwapMinute.objects.filter(symbol=symbol, timestamp_minute__lt=start)
            .order_by('-timestamp_minute')
            .first()
        )
        prev_cum = prev_row.cumulative_volume if prev_row and prev_row.cumulative_volume is not None else None
        window_rows = (
            VwapMinute.objects.filter(symbol=symbol, timestamp_minute__gte=start, timestamp_minute__lte=now_dt)
            .order_by('timestamp_minute')
        )
        numerator = Decimal('0')
        denominator = Decimal('0')
        for r in window_rows:
            if r.last_price is None or r.cumulative_volume is None:
                continue
            if prev_cum is None:
                inc = r.cumulative_volume
            else:
                inc = r.cumulative_volume - prev_cum
            prev_cum = r.cumulative_volume
            if inc is None or inc <= 0:
                continue
            inc_dec = Decimal(str(inc))
            numerator += (r.last_price * inc_dec)
            denominator += inc_dec
        if denominator > 0:
            return (numerator / denominator).quantize(Decimal('0.0001'))
        return None

    # Backwards compatibility for any legacy import expecting get_current_vwap
    def get_current_vwap(self, symbol: str) -> Optional[Decimal]:
        return self.get_today_vwap(symbol)


vwap_service = VwapService()

__all__ = ["vwap_service", "VwapService", "VwapResult"]

