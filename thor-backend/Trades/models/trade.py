from django.db import models
from django.utils import timezone


class Trade(models.Model):
    """Individual fills (can drive Account Statement / P&L)."""

    SIDE_CHOICES = [("BUY", "Buy"), ("SELL", "Sell")]

    exec_id = models.CharField(max_length=64, blank=True)

    symbol = models.CharField(max_length=32)
    side = models.CharField(max_length=4, choices=SIDE_CHOICES)
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    price = models.DecimalField(max_digits=18, decimal_places=6)

    commission = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    fees = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    exec_time = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "ActAndPos_trade"
        verbose_name = "Trade"
        verbose_name_plural = "Trades"

    def __str__(self) -> str:
        return f"{self.account} {self.side} {self.quantity} {self.symbol} @ {self.price}"
