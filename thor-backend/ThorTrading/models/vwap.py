"""
Minimal VWAP sampling model.

Stores a single row per country + symbol per minute capturing raw
snapshot data pulled from Redis (latest quote) without performing any
VWAP math.

Aggregation / VWAP calculations happen elsewhere.

Rows are written by the `capture_vwap_minutes` management command which
reads Redis every N seconds but only persists on minute boundaries.
"""

from django.db import models
from GlobalMarkets.models.constants import CONTROL_COUNTRY_CHOICES


class VwapMinute(models.Model):
    # Market identity (aligns with MarketSession / MarketIntraday / MarketTrading24Hour)
    country = models.CharField(
        max_length=32,
        choices=CONTROL_COUNTRY_CHOICES,
        db_index=True,
        help_text="Market region (canonical values only)",
    )

    symbol = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Instrument symbol (YM, ES, NQ, AAPL, SPY, etc.)",
    )

    timestamp_minute = models.DateTimeField(
        db_index=True,
        help_text="UTC minute (floored)",
    )

    # Raw snapshot data (no VWAP math here)
    last_price = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        null=True,
        blank=True,
    )
    cumulative_volume = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Cumulative volume from feed at sample time",
    )

    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("country", "symbol", "timestamp_minute"),)
        indexes = [
            models.Index(fields=["country", "symbol", "timestamp_minute"], name="idx_vwap_cty_sym_ts"),
            models.Index(fields=["timestamp_minute"], name="idx_vwap_ts"),
        ]
        ordering = ["-timestamp_minute", "country", "symbol"]
        verbose_name = "VWAP Minute"
        verbose_name_plural = "VWAP Minutes"

    def __str__(self):  # pragma: no cover
        return (
            f"VWAPMinute {self.country} {self.symbol} "
            f"{self.timestamp_minute:%Y-%m-%d %H:%M} "
            f"last={self.last_price} vol={self.cumulative_volume}"
        )


__all__ = ["VwapMinute"]
