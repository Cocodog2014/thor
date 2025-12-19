from django.db import models
from .market import Market


class MarketHoliday(models.Model):
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='holidays')
    date = models.DateField()
    full_day = models.BooleanField(default=True)
    description = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['market', 'date']
        ordering = ['market__country', '-date']
        verbose_name = 'Market Holiday'
        verbose_name_plural = 'Market Holidays'

    def __str__(self):
        return f"{self.market.country} holiday on {self.date} ({'Full' if self.full_day else 'Partial'})"