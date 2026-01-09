from __future__ import annotations

from django.db import models


class MarketHoliday(models.Model):
    """
    US Market holidays that apply to ALL markets.
    When a holiday exists, all markets are considered closed.
    """

    date = models.DateField(unique=True)
    name = models.CharField(max_length=120, help_text="Holiday name (e.g., 'Thanksgiving', 'Christmas')")
    is_closed = models.BooleanField(default=True, help_text="Full day closure")
    early_close_time = models.TimeField(
        null=True, 
        blank=True,
        help_text="If set, markets close early at this time (ET)"
    )

    class Meta:
        ordering = ["-date"]
        verbose_name = "US Market Holiday"
        verbose_name_plural = "US Market Holidays"
        indexes = [
            models.Index(fields=["date"]),
        ]

    def __str__(self) -> str:
        if self.is_closed:
            return f"{self.name} - {self.date} (CLOSED)"
        elif self.early_close_time:
            return f"{self.name} - {self.date} (Early close {self.early_close_time})"
        return f"{self.name} - {self.date}"
