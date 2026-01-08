from __future__ import annotations

from django.db import models


class MarketHoliday(models.Model):
    """
    Exceptions to the weekly schedule for a specific market.
    - is_closed=True: closed all day
    - is_closed=False + early_close_time: closes early
    """

    market = models.ForeignKey("GlobalMarkets.Market", on_delete=models.CASCADE, related_name="holidays")
    date = models.DateField()

    name = models.CharField(max_length=120, blank=True, default="")
    is_closed = models.BooleanField(default=True)
    early_close_time = models.TimeField(null=True, blank=True)

    class Meta:
        ordering = ["market_id", "-date"]
        constraints = [
            models.UniqueConstraint(fields=["market", "date"], name="uniq_market_holiday_date")
        ]
        indexes = [
            models.Index(fields=["market", "date"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self) -> str:
        label = "Closed" if self.is_closed else "Open"
        return f"{self.market.key} {self.date} ({label})"
