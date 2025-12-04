from django.db import models

class FutureTrading24Hour(models.Model):
    """
    Rolling 24-hour global session stats (JP→US).
    Continuously updated as ticks arrive; finalized at US close.
    """
    session_group = models.CharField(max_length=32, db_index=True, help_text="Shared key with MarketSession.capture_group")
    session_date = models.DateField(db_index=True)
    country = models.CharField(max_length=32)
    future = models.CharField(max_length=20)
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
        unique_together = (('session_group', 'future'),)
        indexes = [
            models.Index(fields=['session_date', 'country', 'future']),
        ]
        verbose_name = '24-Hour Global Session'
        verbose_name_plural = '24-Hour Global Sessions'
