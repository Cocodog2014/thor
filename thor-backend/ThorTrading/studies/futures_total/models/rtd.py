from __future__ import annotations
"""RTD models.

These models live alongside the `futures_total` study code.

Important: These models are still owned by the `Instruments` Django app.
We keep `Meta.app_label = "Instruments"` so existing migrations, admin labels,
and database table names remain stable.
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
        app_label = "Instruments"
        managed = True
        db_table = "Instruments_instrumentcategory"
        ordering = ["sort_order", "name"]
        verbose_name = "Instrument Category"
        verbose_name_plural = "Instrument Categories"

    def __str__(self) -> str:
        return self.display_name


SIGNAL_CHOICES = [
    ("STRONG_BUY", "Strong Buy"),
    ("BUY", "Buy"),
    ("HOLD", "Hold"),
    ("SELL", "Sell"),
    ("STRONG_SELL", "Strong Sell"),
]


class SignalStatValue(models.Model):
    instrument = models.ForeignKey(
        "Instruments.Instrument",
        on_delete=models.CASCADE,
        related_name="signal_stat_values",
    )
    signal = models.CharField(max_length=20, choices=SIGNAL_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=6)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "Instruments"
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
        app_label = "Instruments"
        managed = True
        db_table = "Instruments_signalweight"
        ordering = ["-weight"]
        verbose_name = "Signal Weight"
        verbose_name_plural = "Signal Weights"

    def __str__(self) -> str:
        return f"{self.get_signal_display()}: {self.weight}"


class ContractWeight(models.Model):
    instrument = models.OneToOneField(
        "Instruments.Instrument",
        on_delete=models.CASCADE,
        related_name="contract_weight",
    )
    weight = models.DecimalField(max_digits=8, decimal_places=6, default=Decimal("1.0"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "Instruments"
        managed = True
        db_table = "Instruments_contractweight"
        ordering = ["instrument__country", "instrument__symbol"]
        verbose_name = "Contract Weight"
        verbose_name_plural = "Contract Weights"

    def __str__(self) -> str:
        return f"{self.instrument.country} {self.instrument.symbol}: {self.weight}"


__all__ = [
    "InstrumentCategory",
    "SIGNAL_CHOICES",
    "SignalStatValue",
    "SignalWeight",
    "ContractWeight",
]
