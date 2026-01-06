from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class UserInstrumentSubscription(models.Model):
    """User-scoped streaming subscription list (used by the Schwab streamer control plane)."""

    ASSET_EQUITY = "EQUITY"
    ASSET_FUTURE = "FUTURE"
    ASSET_INDEX = "INDEX"
    ASSET_OPTION = "OPTION"
    ASSET_BOND = "BOND"
    ASSET_FOREX = "FOREX"
    ASSET_MUTUAL_FUND = "MUTUAL_FUND"

    ASSET_CHOICES = [
        (ASSET_EQUITY, "Equity"),
        (ASSET_FUTURE, "Future"),
        (ASSET_INDEX, "Index"),
        (ASSET_OPTION, "Option"),
        (ASSET_BOND, "Bond"),
        (ASSET_FOREX, "Forex"),
        (ASSET_MUTUAL_FUND, "Mutual Fund"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="schwab_subscriptions",
        help_text="Owner of this Schwab streaming subscription",
    )

    symbol = models.CharField(
        max_length=64,
        help_text="Canonical symbol (e.g., NVDA, /ES, SPX)",
    )

    asset_type = models.CharField(
        max_length=16,
        choices=ASSET_CHOICES,
        default=ASSET_EQUITY,
        help_text="Asset class used to route to the proper streaming service",
    )

    enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Keep the existing table name to avoid churn; this model is simply owned by Instruments now.
        db_table = "schwab_subscription"
        verbose_name = "Schwab Subscription"
        verbose_name_plural = "Schwab Subscriptions"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "symbol", "asset_type"),
                name="uniq_schwab_subscription_user_symbol_asset",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "asset_type"], name="idx_schwab_sub_user_asset"),
            models.Index(fields=["symbol"], name="idx_schwab_sub_symbol"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.asset_type}:{self.symbol}"
