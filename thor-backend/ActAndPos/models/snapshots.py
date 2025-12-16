from __future__ import annotations

from django.db import models
from django.utils import timezone

from .accounts import Account


class AccountDailySnapshot(models.Model):
    """Immutable end-of-day balance capture per account."""

    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="daily_snapshots",
    )
    trading_date = models.DateField(db_index=True)

    net_liq = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    cash = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    equity = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    stock_buying_power = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    option_buying_power = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    day_trading_buying_power = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    raw_payload = models.JSONField(null=True, blank=True)

    captured_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["account", "trading_date"],
                name="uniq_account_daily_snapshot",
            )
        ]
        ordering = ["-trading_date", "-captured_at"]

    def __str__(self) -> str:
        return f"{self.account_id} {self.trading_date} net_liq={self.net_liq}"
