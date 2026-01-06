"""Schwab OAuth token storage.

LiveData (pipes) owns:
- Schwab OAuth / tokens
- Schwab streaming client + Redis conventions

Instruments (runtime product state) owns:
- What symbols should be tracked/subscribed
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

