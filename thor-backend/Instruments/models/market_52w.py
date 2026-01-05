from __future__ import annotations
""""
Rolling 52-Week (and optional All-Time) Extremes

Tracks rolling 52-week highs/lows for any trading instrument identified by
(symbol). Admin seeds initial values; the system auto-updates on
incoming LAST prices.

This model is instrument-neutral and does not assume asset class.
Interpretation of the symbol is handled elsewhere (TradingInstrument).

Signals:
- week52_extreme_changed: fired per extreme update event
  (HIGH_52W, LOW_52W, ALL_TIME_HIGH, ALL_TIME_LOW)
"""


from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union

from django.db import models
from django.utils import timezone
from django.dispatch import Signal


# Event signature:
# (symbol, extreme_type, old_value, new_value, date)
ExtremeEvent = Tuple[str, str, Optional[Decimal], Decimal, timezone.datetime.date]


week52_extreme_changed = Signal()


class Rolling52WeekStatsManager(models.Manager):
    """
    Batch update helper.

    update_batch(prices) accepts mapping: symbol -> last_price (Decimal|str|float|int).
    Updates ONLY existing rows (no auto-create). Returns list of ExtremeEvent tuples.
    """

    def update_batch(self, prices: Dict[str, Union[Decimal, str, float, int]]) -> List[ExtremeEvent]:
        if not prices:
            return []

        # Normalize to Decimal
        normalized: Dict[str, Decimal] = {}
        for sym, val in prices.items():
            try:
                normalized[str(sym).strip()] = Decimal(str(val))
            except Exception:
                continue

        if not normalized:
            return []

        events: List[ExtremeEvent] = []
        for stats in self.filter(symbol__in=list(normalized.keys())):
            events.extend(stats.update_from_price(normalized[stats.symbol], emit_signal=True))
        return events


class Rolling52WeekStats(models.Model):
    """
    Tracks 52-week high/low extremes per trading symbol.

    Workflow:
    1) Admin seeds initial high_52w / low_52w (and their dates)
    2) System updates on new LAST prices that exceed extremes
    3) Optional all-time highs/lows update after seed exists
    """

    symbol = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        help_text="Trading symbol (ES, YM, CL, AAPL, SPY, etc.)"
    )

    # 52-Week High
    high_52w = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        help_text="Highest price in last 52 weeks"
    )
    high_52w_date = models.DateField(
        help_text="Date when the 52-week high was set"
    )

    # 52-Week Low
    low_52w = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        help_text="Lowest price in last 52 weeks"
    )
    low_52w_date = models.DateField(
        help_text="Date when the 52-week low was set"
    )

    # Metadata
    last_price_checked = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Most recent LAST price that was checked"
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text="When this record was last updated"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # Optional All-Time extremes (instrument neutral)
    all_time_high = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="All-time high (optional)"
    )
    all_time_high_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when all-time high was set"
    )

    all_time_low = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="All-time low (optional)"
    )
    all_time_low_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when all-time low was set"
    )

    objects = Rolling52WeekStatsManager()

    class Meta:
        # This is now an Instruments-owned table (source of truth lives here).
        managed = True
        db_table = "Instruments_rolling52weekstats"
        verbose_name = "52-Week Stats"
        verbose_name_plural = "52-Week Stats"
        ordering = ["symbol"]

    def __str__(self) -> str:
        return f"{self.symbol}: 52W(H={self.high_52w} L={self.low_52w})"

    def stale_hours(self) -> Optional[float]:
        """Hours since last_updated; None if missing."""
        if not self.last_updated:
            return None
        delta = timezone.now() - self.last_updated
        return round(delta.total_seconds() / 3600.0, 2)

    def update_from_price(self, last_price: Decimal, emit_signal: bool = False) -> Union[bool, List[ExtremeEvent]]:
        """
        Update extremes based on an incoming LAST price.

        Returns:
          - emit_signal=False: bool indicating whether any extreme changed
          - emit_signal=True: list of ExtremeEvent tuples
        """
        updated = False
        events: List[ExtremeEvent] = []
        today = timezone.localdate()

        # Track last checked price always
        self.last_price_checked = last_price

        # New 52-week high
        if last_price > self.high_52w:
            prev = self.high_52w
            self.high_52w = last_price
            self.high_52w_date = today
            updated = True
            events.append((self.symbol, "HIGH_52W", prev, last_price, today))

            # Optional all-time high (only if seeded)
            if (self.all_time_high is None or last_price > self.all_time_high) and self.low_52w_date and self.high_52w_date:
                prev_at = self.all_time_high
                self.all_time_high = last_price
                self.all_time_high_date = today
                events.append((self.symbol, "ALL_TIME_HIGH", prev_at, last_price, today))

        # New 52-week low
        if last_price < self.low_52w:
            prev = self.low_52w
            self.low_52w = last_price
            self.low_52w_date = today
            updated = True
            events.append((self.symbol, "LOW_52W", prev, last_price, today))

            # Optional all-time low (only if seeded)
            if (self.all_time_low is None or last_price < self.all_time_low) and self.low_52w_date and self.high_52w_date:
                prev_at = self.all_time_low
                self.all_time_low = last_price
                self.all_time_low_date = today
                events.append((self.symbol, "ALL_TIME_LOW", prev_at, last_price, today))

        if updated:
            # auto_now will set last_updated
            self.save(update_fields=[
                "high_52w", "high_52w_date",
                "low_52w", "low_52w_date",
                "all_time_high", "all_time_high_date",
                "all_time_low", "all_time_low_date",
                "last_price_checked",
                "last_updated",
            ])

            if emit_signal and events:
                for (symbol, extreme_type, old_value, new_value, date) in events:
                    week52_extreme_changed.send(
                        sender=Rolling52WeekStats,
                        instance=self,
                        symbol=symbol,
                        extreme_type=extreme_type,
                        old_value=old_value,
                        new_value=new_value,
                        date=date,
                    )

        return events if emit_signal else updated

    def to_dict(self) -> dict:
        """Safe dict for Redis/API serialization."""
        return {
            "symbol": self.symbol,
            "high_52w": str(self.high_52w),
            "high_52w_date": self.high_52w_date.isoformat(),
            "low_52w": str(self.low_52w),
            "low_52w_date": self.low_52w_date.isoformat(),
            "all_time_high": str(self.all_time_high) if self.all_time_high is not None else None,
            "all_time_high_date": self.all_time_high_date.isoformat() if self.all_time_high_date else None,
            "all_time_low": str(self.all_time_low) if self.all_time_low is not None else None,
            "all_time_low_date": self.all_time_low_date.isoformat() if self.all_time_low_date else None,
            "last_price_checked": str(self.last_price_checked) if self.last_price_checked is not None else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "stale_hours": self.stale_hours(),
        }
