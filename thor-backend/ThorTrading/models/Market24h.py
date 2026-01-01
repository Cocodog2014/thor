from __future__ import annotations
from django.db import models
from GlobalMarkets.models.constants import CONTROL_COUNTRY_CHOICES


class MarketTrading24Hour(models.Model):
    """
    Rolling 24-hour global session stats (JP→US).
    Continuously updated as ticks arrive; finalized at US close.

    Instrument-neutral: futures, equities, ETFs, indexes, etc.
    """
    session_group = models.IntegerField(
        db_index=True,
        help_text="Shared key with MarketSession.session_number",
    )
    session_date = models.DateField(db_index=True)

    country = models.CharField(
        max_length=32,
        choices=CONTROL_COUNTRY_CHOICES,
        help_text="Market region (canonical values only)",
    )

    symbol = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Instrument symbol (e.g., ES, YM, NQ, AAPL, SPY)",
    )

    prev_close_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    open_price_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    open_prev_diff_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    open_prev_pct_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    low_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    high_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    range_diff_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    range_pct_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    close_24h = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    volume_24h = models.BigIntegerField(null=True, blank=True, help_text="Cumulative volume across JP→US window")
    finalized = models.BooleanField(default=False, help_text="True when US close is reached")

    class Meta:
        unique_together = (("session_group", "country", "symbol"),)
        indexes = [
            models.Index(fields=["session_date", "country", "symbol"]),
        ]
        verbose_name = "24-Hour Global Session"
        verbose_name_plural = "24-Hour Global Sessions"

    def __str__(self):
        return f"{self.country} {self.symbol} {self.session_date} (group={self.session_group})"
