from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class LiveBalance(models.Model):
    """Current broker-reported balance snapshot."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_balances")
    broker = models.CharField(max_length=20, default="SCHWAB")
    broker_account_id = models.CharField(max_length=128, db_index=True)

    currency = models.CharField(max_length=8, default="USD")

    net_liq = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    cash = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    equity = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))

    stock_buying_power = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    option_buying_power = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    day_trading_buying_power = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))

    broker_payload = models.JSONField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "broker", "broker_account_id"],
                name="uniq_live_balance_user_broker_account",
            ),
        ]


class LivePosition(models.Model):
    """Current broker-reported position snapshot."""

    ASSET_TYPE_CHOICES = [
        ("EQ", "Equity"),
        ("FUT", "Future"),
        ("OPT", "Option"),
        ("FX", "Forex"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_positions")
    broker = models.CharField(max_length=20, default="SCHWAB")
    broker_account_id = models.CharField(max_length=128, db_index=True)

    symbol = models.CharField(max_length=32)
    description = models.CharField(max_length=128, blank=True)
    asset_type = models.CharField(max_length=8, choices=ASSET_TYPE_CHOICES, default="EQ")

    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))
    avg_price = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    mark_price = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))

    broker_pl_day = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    broker_pl_ytd = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))

    multiplier = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("1"))
    currency = models.CharField(max_length=8, default="USD")

    broker_payload = models.JSONField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "broker", "broker_account_id", "symbol", "asset_type"],
                name="uniq_live_position",
            ),
        ]


class LiveOrder(models.Model):
    """Broker order record (working/filled/canceled/etc)."""

    SIDE_CHOICES = [("BUY", "Buy"), ("SELL", "Sell")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_orders")
    broker = models.CharField(max_length=20, default="SCHWAB")
    broker_account_id = models.CharField(max_length=128, db_index=True)

    broker_order_id = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=32, default="WORKING")

    symbol = models.CharField(max_length=32)
    asset_type = models.CharField(max_length=8, default="EQ")
    side = models.CharField(max_length=4, choices=SIDE_CHOICES)
    quantity = models.DecimalField(max_digits=18, decimal_places=4)

    order_type = models.CharField(max_length=16, default="LMT")
    limit_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    stop_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)

    broker_payload = models.JSONField(null=True, blank=True)

    time_placed = models.DateTimeField(default=timezone.now)
    time_last_update = models.DateTimeField(auto_now=True)


class LiveExecution(models.Model):
    """Optional broker execution/fill detail."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_executions")
    broker = models.CharField(max_length=20, default="SCHWAB")
    broker_account_id = models.CharField(max_length=128, db_index=True)

    broker_exec_id = models.CharField(max_length=128, blank=True)
    order = models.ForeignKey(LiveOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name="executions")

    symbol = models.CharField(max_length=32)
    side = models.CharField(max_length=4)
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    price = models.DecimalField(max_digits=18, decimal_places=6)

    commission = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    fees = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))

    exec_time = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["broker_account_id", "exec_time"], name="idx_live_exec_acct_time"),
        ]
