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

    symbol = models.CharField(max_length=32, unique=True, db_index=True)
    asset_type = models.CharField(max_length=16, choices=AssetType.choices)

    name = models.CharField(max_length=128, blank=True)
    exchange = models.CharField(max_length=32, blank=True)  # NASDAQ, NYSE, CME, etc
    currency = models.CharField(max_length=8, blank=True, default="USD")

    # optional precision metadata (useful later)
    tick_size = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    point_value = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.symbol} ({self.asset_type})"
