from __future__ import annotations
"""
Real-Time Data (RTD) models

Core models used to describe instruments and their classification/weighting.
Instrument-neutral: supports futures, equities, ETFs, crypto, FX, etc.
"""

from django.db import models
from decimal import Decimal


class InstrumentCategory(models.Model):
    """Categories for different types of trading instruments"""
    name = models.CharField(max_length=50, unique=True)  # e.g., 'futures', 'stocks', 'crypto', 'forex'
    display_name = models.CharField(max_length=100)  # e.g., 'Futures Contracts', 'Stocks & ETFs'
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    # Display configuration
    color_primary = models.CharField(max_length=7, default="#4CAF50")  # Hex color for UI
    color_secondary = models.CharField(max_length=7, default="#81C784")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Instrument Category"
        verbose_name_plural = "Instrument Categories"

    def __str__(self):
        return self.display_name


class TradingInstrument(models.Model):
    """Flexible model for any type of trading instrument"""

    # Market identity (aligns with MarketSession.country / MarketTrading24Hour.country / MarketIntraday.country)
    country = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Market region (canonical values only)",
    )

    # Basic identification
    symbol = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Canonical instrument code (e.g., NQ, ES, AAPL)",
    )
    name = models.CharField(max_length=200)  # e.g., 'Nasdaq 100 Futures', 'Apple Inc'
    description = models.TextField(blank=True)

    # Categorization
    category = models.ForeignKey(InstrumentCategory, on_delete=models.CASCADE, related_name="instruments")

    # Market information
    exchange = models.CharField(max_length=50, blank=True)  # e.g., 'CME', 'NASDAQ', 'Binance'
    currency = models.CharField(max_length=10, default="USD")

    # Trading configuration
    is_active = models.BooleanField(default=True, db_index=True)
    is_watchlist = models.BooleanField(default=False)  # Show in main watchlist
    show_in_ribbon = models.BooleanField(default=False)  # Show in moving ticker ribbon
    sort_order = models.IntegerField(default=0)

    # Display configuration
    display_precision = models.IntegerField(default=2)  # Decimal places to show
    tick_size = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    contract_size = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Trading calculations
    tick_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Dollar value per tick/point movement",
    )
    margin_requirement = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Margin required per contract in USD",
    )

    # API configuration
    api_provider = models.CharField(max_length=50, blank=True)  # 'alpha_vantage', 'iex', 'polygon'
    api_symbol = models.CharField(max_length=100, blank=True)  # Symbol as used by API provider
    feed_symbol = models.CharField(
        max_length=100,
        blank=True,
        help_text="Raw feed symbol (/NQ, NQH26, etc.) when different from canonical code",
    )
    update_frequency = models.IntegerField(default=5)  # Seconds between updates

    # Status
    last_updated = models.DateTimeField(null=True, blank=True)
    is_market_open = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "country", "symbol"]
        unique_together = [("country", "symbol")]
        indexes = [
            models.Index(fields=["country", "symbol"], name="idx_instr_country_symbol"),
            models.Index(fields=["country", "is_active"], name="idx_instr_country_active"),
            models.Index(fields=["category", "sort_order"], name="idx_instr_category_sort"),
        ]
        verbose_name = "Trading Instrument"
        verbose_name_plural = "Trading Instruments"

    def __str__(self):
        return f"{self.country} {self.symbol} - {self.name}"


# Signal choices used by SignalStatValue and SignalWeight
SIGNAL_CHOICES = [
    ("STRONG_BUY", "Strong Buy"),
    ("BUY", "Buy"),
    ("HOLD", "Hold"),
    ("SELL", "Sell"),
    ("STRONG_SELL", "Strong Sell"),
]


class SignalStatValue(models.Model):
    """Statistical values mapped from trading signals per instrument"""
    instrument = models.ForeignKey(
        TradingInstrument,
        on_delete=models.CASCADE,
        related_name="signal_stat_values",
    )
    signal = models.CharField(max_length=20, choices=SIGNAL_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=6)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("instrument", "signal")]
        ordering = ["instrument__country", "instrument__symbol", "signal"]
        verbose_name = "Signal Statistical Value"
        verbose_name_plural = "Signal Statistical Values"

    def __str__(self):
        return f"{self.instrument.country} {self.instrument.symbol} - {self.get_signal_display()}: {self.value}"


class SignalWeight(models.Model):
    """Weight values for signals (e.g., Strong Buy=2, Buy=1, Hold=0, Sell=-1, Strong Sell=-2)"""
    signal = models.CharField(max_length=20, choices=SIGNAL_CHOICES, unique=True)
    weight = models.IntegerField(help_text="Weight value for this signal type (e.g., 2, 1, 0, -1, -2)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-weight"]  # Strong Buy first, Strong Sell last
        verbose_name = "Signal Weight"
        verbose_name_plural = "Signal Weights"

    def __str__(self):
        return f"{self.get_signal_display()}: {self.weight}"


class ContractWeight(models.Model):
    """Weights for how much each instrument influences the total composite score"""
    instrument = models.OneToOneField(
        TradingInstrument,
        on_delete=models.CASCADE,
        related_name="contract_weight",
    )
    weight = models.DecimalField(max_digits=8, decimal_places=6, default=Decimal("1.0"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["instrument__country", "instrument__symbol"]
        verbose_name = "Contract Weight"
        verbose_name_plural = "Contract Weights"

    def __str__(self):
        return f"{self.instrument.country} {self.instrument.symbol}: {self.weight}"


__all__ = [
    "InstrumentCategory",
    "TradingInstrument",
    "SIGNAL_CHOICES",
    "SignalStatValue",
    "SignalWeight",
    "ContractWeight",
]

