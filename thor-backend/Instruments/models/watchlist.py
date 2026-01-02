from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models

from .instrument import Instrument

User = get_user_model()


class UserInstrumentWatchlistItem(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="instrument_watchlist_items",
    )
    instrument = models.ForeignKey(
        Instrument,
        on_delete=models.CASCADE,
        related_name="watchlisted_by",
    )

    enabled = models.BooleanField(default=True)
    stream = models.BooleanField(
        default=True,
        help_text="If true, this symbol should be subscribed on the live feed.",
    )
    order = models.IntegerField(default=0, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Instrument Watchlist Item"
        verbose_name_plural = "User Instrument Watchlist Items"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "instrument"),
                name="uniq_user_instrument_watchlist_item",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "order"], name="idx_watchlist_user_order"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.instrument.symbol}"
