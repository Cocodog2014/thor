from django.db import models

class MarketIntraday(models.Model):
    """
    1-minute OHLCV bars for each future, every minute.
    Used for charting, ML, and building higher timeframe candles.
    """
    timestamp_minute = models.DateTimeField(db_index=True, help_text="Minute bucket (UTC)")
    country = models.CharField(max_length=10, help_text="Market region (e.g., USA, JPN, LON)")
    future = models.CharField(max_length=10, help_text="Future symbol (e.g., ES, YM, NQ)")
    market_code = models.CharField(max_length=10, help_text="Market code (e.g., USA, JPN, LON)")
    twentyfour = models.ForeignKey('FutureTrading24Hour', on_delete=models.CASCADE, related_name='intraday_bars')
    open_1m = models.DecimalField(max_digits=14, decimal_places=4)
    high_1m = models.DecimalField(max_digits=14, decimal_places=4)
    low_1m = models.DecimalField(max_digits=14, decimal_places=4)
    close_1m = models.DecimalField(max_digits=14, decimal_places=4)
    volume_1m = models.BigIntegerField()
    bid_last = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    ask_last = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    spread_last = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    class Meta:
        unique_together = (('timestamp_minute', 'future', 'country'),)
        indexes = [
            models.Index(fields=['twentyfour']),
        ]
        verbose_name = 'Market Intraday Bar'
        verbose_name_plural = 'Market Intraday Bars'
