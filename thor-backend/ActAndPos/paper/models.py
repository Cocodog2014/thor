from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class PaperBalance(models.Model):
    """Current simulated balance snapshot for a paper trading account."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="paper_balances")
    account_key = models.CharField(max_length=64, db_index=True, help_text="Client-facing account identifier")

    currency = models.CharField(max_length=8, default="USD")

    cash = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    equity = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    net_liq = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))

    buying_power = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    day_trade_bp = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))

    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "account_key"], name="uniq_paper_balance_user_account"),
        ]


class PaperPosition(models.Model):
    """Current simulated position snapshot for a paper trading account."""

    ASSET_TYPE_CHOICES = [
        ("EQ", "Equity"),
        ("FUT", "Future"),
        ("OPT", "Option"),
        ("FX", "Forex"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="paper_positions")
    account_key = models.CharField(max_length=64, db_index=True)

    symbol = models.CharField(max_length=32)
    description = models.CharField(max_length=128, blank=True)
    asset_type = models.CharField(max_length=8, choices=ASSET_TYPE_CHOICES, default="EQ")

    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))
    avg_price = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    mark_price = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))

    realized_pl_day = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    realized_pl_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))

    multiplier = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("1"))
    currency = models.CharField(max_length=8, default="USD")

    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "account_key", "symbol", "asset_type"], name="uniq_paper_position"),
        ]

    @property
    def market_value(self):
        return (self.quantity or Decimal("0")) * (self.mark_price or Decimal("0")) * (self.multiplier or Decimal("1"))


class PaperOrder(models.Model):
    """Simulated order record for paper execution."""

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

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="paper_orders")
    account_key = models.CharField(max_length=64, db_index=True)

    client_order_id = models.CharField(max_length=64, blank=True, help_text="Client-generated identifier")

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


class PaperFill(models.Model):
    """A simulated execution fill for a paper order."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="paper_fills")
    account_key = models.CharField(max_length=64, db_index=True)
    order = models.ForeignKey(PaperOrder, on_delete=models.CASCADE, related_name="fills")

    exec_id = models.CharField(max_length=64, blank=True)

    symbol = models.CharField(max_length=32)
    side = models.CharField(max_length=4)
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    price = models.DecimalField(max_digits=18, decimal_places=6)

    commission = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    fees = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))

    exec_time = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["account_key", "exec_time"], name="idx_paper_fill_acct_time"),
        ]
