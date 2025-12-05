from django.db import models
from django.utils import timezone


class Order(models.Model):
    """Orders for today's trade activity (working / filled / canceled)."""

    SIDE_CHOICES = [("BUY", "Buy"), ("SELL", "Sell")]
    STATUS_CHOICES = [
        ("WORKING", "Working"),
        ("FILLED", "Filled"),
        ("CANCELED", "Canceled"),
        ("PARTIAL", "Partially Filled"),
        ("REJECTED", "Rejected"),
    ]
    ORDER_TYPE_CHOICES = [
        ("MKT", "Market"),
        ("LMT", "Limit"),
        ("STP", "Stop"),
        ("STP_LMT", "Stop Limit"),
    ]

    account = models.ForeignKey(
        "ActAndPos.Account",
        on_delete=models.CASCADE,
        related_name="orders",
    )
    broker_order_id = models.CharField(max_length=64, blank=True)

    symbol = models.CharField(max_length=32)
    asset_type = models.CharField(max_length=8, default="EQ")
    side = models.CharField(max_length=4, choices=SIDE_CHOICES)
    quantity = models.DecimalField(max_digits=18, decimal_places=4)

    order_type = models.CharField(max_length=16, choices=ORDER_TYPE_CHOICES, default="LMT")
    limit_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    stop_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="WORKING")

    time_placed = models.DateTimeField(default=timezone.now)
    time_last_update = models.DateTimeField(auto_now=True)
    time_canceled = models.DateTimeField(null=True, blank=True)
    time_filled = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.account} {self.side} {self.quantity} {self.symbol} ({self.status})"
