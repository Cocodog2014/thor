"""
Schwab OAuth token storage.

This is the ONLY model in the Schwab app - just stores OAuth tokens per user.
All other data (positions, balances, orders) comes from the API in real-time
and is published to Redis for consumption by other apps.
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class BrokerConnection(models.Model):
    """Stores OAuth access for any supported broker (currently Schwab)."""

    BROKER_SCHWAB = "SCHWAB"

    BROKER_CHOICES = [
        (BROKER_SCHWAB, "Charles Schwab"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="broker_connections",
        help_text="Thor user who owns this broker connection",
    )

    broker = models.CharField(
        max_length=32,
        choices=BROKER_CHOICES,
        default=BROKER_SCHWAB,
        help_text="Broker identifier (e.g. SCHWAB)",
    )

    access_token = models.TextField(
        help_text="Short-lived OAuth access token (typically 30 minutes)"
    )

    refresh_token = models.TextField(
        help_text="Long-lived refresh token (typically 7 days)"
    )

    access_expires_at = models.BigIntegerField(
        help_text="Unix timestamp when access token expires"
    )

    broker_account_id = models.CharField(
        max_length=64,
        blank=True,
        help_text="Primary broker account ID (if cached)",
    )

    trading_enabled = models.BooleanField(
        default=False,
        help_text="When true, Thor may send live orders for this connection.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "broker_connection"
        verbose_name = "Broker Connection"
        verbose_name_plural = "Broker Connections"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "broker"), name="unique_user_broker_connection"
            )
        ]

    def __str__(self):
        broker_name = dict(self.BROKER_CHOICES).get(self.broker, self.broker)
        return f"{broker_name} connection for {self.user.email}"

    @property
    def is_expired(self) -> bool:
        """Check if access token is expired."""
        import time

        return time.time() >= self.access_expires_at


class SchwabSubscription(models.Model):
    """User-scoped streaming subscription list for Schwab feeds."""

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
        help_text="Asset class used to route to the proper Schwab streaming service",
    )

    enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
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
