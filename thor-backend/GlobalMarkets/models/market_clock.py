# GlobalMarkets/models/market_clock.py

from django.db import models
from django.utils import timezone


class Market(models.Model):
    """
    One 'global market clock' configured in Admin.
    Persisted status is updated ONLY on transitions (not every second).
    """

    class Status(models.TextChoices):
        CLOSED = "CLOSED", "Closed"
        PREMARKET = "PREMARKET", "Premarket"
        OPEN = "OPEN", "Open"

    key = models.SlugField(
        max_length=40,
        unique=True,
        help_text="Stable identifier used by API/WS. Example: 'new_york', 'london', 'tokyo'.",
    )
    name = models.CharField(max_length=80)
    country = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text="Display label for the Country column (admin-controlled). Example: 'Japan', 'United Kingdom'.",
    )
    timezone_name = models.CharField(
        max_length=64,
        help_text="IANA timezone. Example: 'America/New_York', 'Europe/London'.",
    )
    
    # Default trading hours (used if no sessions defined)
    open_time = models.TimeField(
        null=True, 
        blank=True, 
        help_text="Default market open time (local timezone). Example: 09:00"
    )
    close_time = models.TimeField(
        null=True, 
        blank=True, 
        help_text="Default market close time (local timezone). Example: 16:00"
    )

    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CLOSED)
    status_changed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["is_active", "sort_order"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.key})"

    def mark_status(self, new_status: str, when=None) -> bool:
        """
        Update persisted status only when it changes.
        Returns True if a change was saved.
        """
        if new_status == self.status:
            return False

        self.status = new_status
        self.status_changed_at = when or timezone.now()
        self.save(update_fields=["status", "status_changed_at", "updated_at"])
        return True


class MarketStatusEvent(models.Model):
    """
    Immutable audit log of market OPEN / CLOSED transitions.

    One row is written only when a market status actually changes.
    Used for admin filtering by market and date.
    """

    market = models.ForeignKey(
        "GlobalMarkets.Market",
        on_delete=models.CASCADE,
        related_name="status_events",
        db_index=True,
    )

    # Expect values like: "OPEN", "CLOSED"
    old_status = models.CharField(max_length=12)
    new_status = models.CharField(max_length=12)

    # UTC timestamp of the transition
    changed_at = models.DateTimeField(db_index=True)

    # Optional: computed next transition time at the moment of status change
    # (kept for migration/model consistency and potential UI use)
    next_transition_utc = models.DateTimeField(null=True, blank=True)

    # Optional but useful for debugging / ops
    reason = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["-changed_at"]
        indexes = [
            models.Index(fields=["market", "-changed_at"]),
            models.Index(fields=["new_status", "-changed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.market.key}: {self.old_status} -> {self.new_status} @ {self.changed_at}"
