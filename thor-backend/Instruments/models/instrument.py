from __future__ import annotations

from django.db import models


class Instrument(models.Model):
    class AssetType(models.TextChoices):
        EQUITY = "EQUITY", "Equity"
        FUTURE = "FUTURE", "Future"
        ETF = "ETF", "ETF"
        INDEX = "INDEX", "Index"
        FOREX = "FOREX", "Forex"
        CRYPTO = "CRYPTO", "Crypto"

    class QuoteSource(models.TextChoices):
        AUTO = "AUTO", "Auto"
        SCHWAB = "SCHWAB", "Schwab"
        TOS = "TOS", "ThinkOrSwim"

    symbol = models.CharField(max_length=32, unique=True, db_index=True)
    asset_type = models.CharField(max_length=16, choices=AssetType.choices)

    quote_source = models.CharField(
        max_length=16,
        choices=QuoteSource.choices,
        default=QuoteSource.AUTO,
        help_text="Which feed should be treated as the source of truth for this symbol.",
    )

    name = models.CharField(max_length=128, blank=True)
    exchange = models.CharField(max_length=32, blank=True)  # NASDAQ, NYSE, CME, etc
    currency = models.CharField(max_length=8, blank=True, default="USD")

    # Optional market tagging / UI defaults
    country = models.CharField(
        max_length=32,
        blank=True,
        db_index=True,
        help_text="Market region (canonical values only)",
    )
    sort_order = models.IntegerField(default=0)

    # Display configuration (defaulted for safe legacy compatibility)
    display_precision = models.IntegerField(default=2, help_text="Decimal places to show")

    # optional precision metadata (useful later)
    tick_size = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    point_value = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)

    margin_requirement = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Margin required per contract in USD (if applicable)",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.symbol} ({self.asset_type})"

    @property
    def tick_value(self):
        """Dollar value per tick movement.

        Back-compat: legacy models stored this as a DB field; for Instrument we derive
        it from tick_size * point_value when available.
        """

        if self.tick_size is None or self.point_value is None:
            return None
        try:
            return self.tick_size * self.point_value
        except Exception:
            return None
