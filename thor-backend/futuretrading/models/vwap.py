"""Minimal VWAP sampling model.

This table stores a single row per symbol per minute capturing raw
snapshot data pulled from Redis (latest quote) without performing any
VWAP math. Aggregation / VWAP calculations happen elsewhere in the
FutureTrading app.

Rows are written by the `capture_vwap_minutes` management command which
reads Redis every N seconds but only persists on minute boundaries.
"""

from __future__ import annotations

from django.db import models


class VwapMinute(models.Model):
    symbol = models.CharField(max_length=20)
    timestamp_minute = models.DateTimeField(help_text="UTC minute (floored)")

    last_price = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    cumulative_volume = models.BigIntegerField(null=True, blank=True, help_text="Cumulative volume from feed at sample time")

    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("symbol", "timestamp_minute")
        indexes = [
            models.Index(fields=["symbol", "timestamp_minute"]),
        ]
        ordering = ["-timestamp_minute", "symbol"]

    def __str__(self):  # pragma: no cover
        return f"VWAPMinute {self.symbol} {self.timestamp_minute:%Y-%m-%d %H:%M} last={self.last_price} vol={self.cumulative_volume}"

__all__ = ["VwapMinute"]
