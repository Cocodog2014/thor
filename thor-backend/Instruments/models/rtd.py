from __future__ import annotations
"""RTD models.

These tables are owned by the Instruments app.
"""

from decimal import Decimal

from django.db import models


class InstrumentCategory(models.Model):
    """Categories for different types of trading instruments."""

    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    # Display configuration
    color_primary = models.CharField(max_length=7, default="#4CAF50")
    color_secondary = models.CharField(max_length=7, default="#81C784")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "Instruments_instrumentcategory"
        ordering = ["sort_order", "name"]
        verbose_name = "Instrument Category"
        verbose_name_plural = "Instrument Categories"

    def __str__(self) -> str:
        return self.display_name


class TradingInstrument(models.Model):
    """Legacy trading instrument configuration table."""

    country = models.CharField(max_length=32, db_index=True)
    symbol = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    category = models.ForeignKey(InstrumentCategory, on_delete=models.CASCADE, related_name="instruments")

    exchange = models.CharField(max_length=50, blank=True)
    currency = models.CharField(max_length=10, default="USD")

    is_active = models.BooleanField(default=True, db_index=True)
    is_watchlist = models.BooleanField(default=False)
    show_in_ribbon = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    display_precision = models.IntegerField(default=2)
    tick_size = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    contract_size = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    tick_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    margin_requirement = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    api_provider = models.CharField(max_length=50, blank=True)
    api_symbol = models.CharField(max_length=100, blank=True)
    feed_symbol = models.CharField(max_length=100, blank=True)
    update_frequency = models.IntegerField(default=5)

    last_updated = models.DateTimeField(null=True, blank=True)
    is_market_open = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "Instruments_tradinginstrument"
        ordering = ["sort_order", "country", "symbol"]
        unique_together = [("country", "symbol")]
        indexes = [
            models.Index(fields=["country", "symbol"], name="idx_instr_country_symbol"),
            models.Index(fields=["country", "is_active"], name="idx_instr_country_active"),
            models.Index(fields=["category", "sort_order"], name="idx_instr_category_sort"),
        ]
        verbose_name = "Trading Instrument"
        verbose_name_plural = "Trading Instruments"

    def __str__(self) -> str:
        return f"{self.country} {self.symbol} - {self.name}"


SIGNAL_CHOICES = [
    ("STRONG_BUY", "Strong Buy"),
    ("BUY", "Buy"),
    ("HOLD", "Hold"),
    ("SELL", "Sell"),
    ("STRONG_SELL", "Strong Sell"),
]


class SignalStatValue(models.Model):
    instrument = models.ForeignKey(TradingInstrument, on_delete=models.CASCADE, related_name="signal_stat_values")
    signal = models.CharField(max_length=20, choices=SIGNAL_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=6)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "Instruments_signalstatvalue"
        unique_together = [("instrument", "signal")]
        ordering = ["instrument__country", "instrument__symbol", "signal"]
        verbose_name = "Signal Statistical Value"
        verbose_name_plural = "Signal Statistical Values"

    def __str__(self) -> str:
        return f"{self.instrument.country} {self.instrument.symbol} - {self.get_signal_display()}: {self.value}"


class SignalWeight(models.Model):
    signal = models.CharField(max_length=20, choices=SIGNAL_CHOICES, unique=True)
    weight = models.IntegerField(help_text="Weight value for this signal type")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "Instruments_signalweight"
        ordering = ["-weight"]
        verbose_name = "Signal Weight"
        verbose_name_plural = "Signal Weights"

    def __str__(self) -> str:
        return f"{self.get_signal_display()}: {self.weight}"


class ContractWeight(models.Model):
    instrument = models.OneToOneField(TradingInstrument, on_delete=models.CASCADE, related_name="contract_weight")
    weight = models.DecimalField(max_digits=8, decimal_places=6, default=Decimal("1.0"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "Instruments_contractweight"
        ordering = ["instrument__country", "instrument__symbol"]
        verbose_name = "Contract Weight"
        verbose_name_plural = "Contract Weights"

    def __str__(self) -> str:
        return f"{self.instrument.country} {self.instrument.symbol}: {self.weight}"


__all__ = [
    "InstrumentCategory",
    "TradingInstrument",
    "SIGNAL_CHOICES",
    "SignalStatValue",
    "SignalWeight",
    "ContractWeight",
]
