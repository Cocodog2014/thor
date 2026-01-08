from __future__ import annotations

from django.db import models


class MarketSession(models.Model):
    """
    Weekly schedule. One row per weekday per market.
    weekday: 0=Mon ... 6=Sun
    """

    market = models.ForeignKey("GlobalMarkets.Market", on_delete=models.CASCADE, related_name="sessions")
    weekday = models.PositiveSmallIntegerField(help_text="0=Mon ... 6=Sun")

    is_closed = models.BooleanField(
        default=False,
        help_text="If true, the market is always closed on this weekday.",
    )

    premarket_open_time = models.TimeField(null=True, blank=True)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)

    class Meta:
        ordering = ["market_id", "weekday"]
        constraints = [
            models.UniqueConstraint(fields=["market", "weekday"], name="uniq_market_session_weekday")
        ]
        indexes = [
            models.Index(fields=["market", "weekday"]),
        ]

    def __str__(self) -> str:
        return f"{self.market.key} weekday={self.weekday}"
