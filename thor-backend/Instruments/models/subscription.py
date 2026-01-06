from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()
class SchwabSubscription(models.Model):
    """User-scoped streaming subscription list (product state).

    LiveData consumes this model to decide what to subscribe to, but LiveData does not
    *own* subscription state.
    """

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
        # Non-destructive: keep the legacy LiveData table intact; write new state into an Instruments-owned table.
        db_table = "instrument_schwab_subscription"
        verbose_name = "Schwab Subscription"
        verbose_name_plural = "Schwab Subscriptions"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "symbol", "asset_type"),
                name="uq_isub_usr_sym_ast",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "asset_type"], name="ix_isub_usr_ast"),
            models.Index(fields=["symbol"], name="ix_isub_sym"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.asset_type}:{self.symbol}"

