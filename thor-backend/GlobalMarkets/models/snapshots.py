from django.db import models
from .market import Market


class MarketDataSnapshot(models.Model):
    """
    Real-time market data snapshots - only collected when US markets are open
    """
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='snapshots')
    collected_at = models.DateTimeField(auto_now_add=True)
    market_year = models.IntegerField()
    market_month = models.IntegerField()
    market_date = models.IntegerField()
    market_day = models.CharField(max_length=3)
    market_time = models.TimeField()
    market_status = models.CharField(max_length=10)
    utc_offset = models.CharField(max_length=10)
    dst_active = models.BooleanField()
    is_in_trading_hours = models.BooleanField()

    class Meta:
        ordering = ['-collected_at']
        verbose_name = 'Market Data Snapshot'
        verbose_name_plural = 'Market Data Snapshots'
        indexes = [
            models.Index(fields=['market', '-collected_at']),
            models.Index(fields=['market_status']),
        ]

    def __str__(self):
        return f"{self.market.country} - {self.market_status} at {self.collected_at}"
