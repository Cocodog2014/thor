from django.db import models
from django.utils import timezone

from .orders import Order


class Trade(models.Model):
    """Individual fills (can drive Account Statement / P&L)."""

    account = models.ForeignKey(
        "ActAndPos.Account",
        on_delete=models.CASCADE,
        related_name="trades",
    )
    order = models.ForeignKey(
        "ActAndPos.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trades",
    )

    exec_id = models.CharField(max_length=64, blank=True)

    symbol = models.CharField(max_length=32)
    side = models.CharField(max_length=4, choices=Order.SIDE_CHOICES)
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    price = models.DecimalField(max_digits=18, decimal_places=6)

    commission = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    fees = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    exec_time = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.account} {self.side} {self.quantity} {self.symbol} @ {self.price}"
