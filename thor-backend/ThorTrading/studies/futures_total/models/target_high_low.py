from __future__ import annotations
"""
Target High / Low Configuration Model

Per-instrument configurable offsets used to derive `target_high` and
`target_low` for a `MarketSession` when market open signals are captured.

This version is aligned with the new instrument-neutral naming:
- Uses `country` + `symbol` to match MarketSession / MarketIntraday / TargetHighLowConfig
- MarketTrading24Hour is `session_group` + `symbol` (global, no country)
- Quantization is driven by TradingInstrument.display_precision (caller can pass quant or precision)

Modes:
- POINTS: absolute offsets (e.g., ES +/- 25.00)
- PERCENT: percentage offsets (e.g., VX +/- 0.50% as 0.50)
- DISABLED: no targets computed
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class TargetHighLowConfig(models.Model):
    MODE_POINTS = "POINTS"
    MODE_PERCENT = "PERCENT"
    MODE_DISABLED = "DISABLED"

    MODE_CHOICES = [
        (MODE_POINTS, "Points"),
        (MODE_PERCENT, "Percent"),
        (MODE_DISABLED, "Disabled"),
    ]

    # Align with TradingInstrument (country + symbol uniqueness)
    country = models.CharField(
        max_length=32,
        db_index=True,
        null=False,
        blank=False,
        help_text="Market region (canonical values only)",
    )

    symbol = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Instrument symbol (YM, ES, NQ, RTY, CL, SI, HG, GC, VX, DX, ZB, AAPL, SPY, etc.)",
    )

    mode = models.CharField(
        max_length=10,
        choices=MODE_CHOICES,
        default=MODE_POINTS,
        help_text=(
            "Computation mode: Points adds/subtracts fixed amounts; "
            "Percent uses percentage offsets; Disabled skips target calculation."
        ),
    )

    # Point offsets (absolute magnitudes) - required if mode=POINTS
    offset_high = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Absolute points above entry (BUY target / SELL stop)",
    )
    offset_low = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Absolute points below entry (BUY stop / SELL target)",
    )

    # Percent offsets (required if mode=PERCENT) - expressed as percent (0.50 => 0.50%)
    percent_high = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Percent above entry (e.g. 0.50 = +0.50%)",
    )
    percent_low = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Percent below entry (e.g. 0.50 = -0.50%)",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Deactivate without deleting. If inactive or disabled, targets are not computed.",
    )

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Target High/Low Config"
        verbose_name_plural = "Target High/Low Configs"
        ordering = ["country", "symbol"]
        unique_together = (("country", "symbol"),)
        indexes = [
            models.Index(fields=["country", "symbol"], name="idx_thlc_country_symbol"),
            models.Index(fields=["country", "is_active"], name="idx_thlc_country_active"),
        ]

    def __str__(self):  # pragma: no cover
        prefix = f"{self.country} {self.symbol}"
        if self.mode == self.MODE_POINTS:
            return f"{prefix}: +{self.offset_high} / -{self.offset_low} pts"
        if self.mode == self.MODE_PERCENT:
            return f"{prefix}: +{self.percent_high}% / -{self.percent_low}%"
        return f"{prefix}: (disabled)"

    def clean(self):
        # Ensure required fields for each mode
        if self.mode == self.MODE_POINTS:
            if self.offset_high is None or self.offset_low is None:
                raise ValidationError("Points mode requires offset_high and offset_low")
            if self.offset_high <= 0 or self.offset_low <= 0:
                raise ValidationError(
                    "Point offsets must be positive values (enter absolute magnitudes, no minus sign)"
                )

        elif self.mode == self.MODE_PERCENT:
            if self.percent_high is None or self.percent_low is None:
                raise ValidationError("Percent mode requires percent_high and percent_low")
            if self.percent_high <= 0 or self.percent_low <= 0:
                raise ValidationError(
                    "Percent offsets must be positive (e.g. 0.50 for +0.50%)"
                )

    def compute_targets(
        self,
        entry_price: Decimal,
        quant: Decimal | None = None,
        *,
        precision: int | None = None,
    ):
        """
        Return (target_high, target_low) or None if disabled/inactive.

        Percent interpretation:
          percent_high=0.50 means +0.50%  -> multiply by (1 + 0.50/100)

        Quantization:
          - If `quant` is provided (e.g. Decimal("0.01")), uses that.
          - Else if `precision` is provided, quant is derived as Decimal("1").scaleb(-precision).
          - Else returns raw Decimals (caller can quantize).
        """
        if entry_price is None:
            raise ValueError("entry_price is required to compute targets")

        if not self.is_active or self.mode == self.MODE_DISABLED:
            return None

        if quant is None and precision is not None:
            # precision=2 -> 0.01
            quant = Decimal("1").scaleb(-precision)

        def _q(val: Decimal) -> Decimal:
            return val.quantize(quant) if quant is not None else val

        if self.mode == self.MODE_POINTS:
            high = _q(entry_price + self.offset_high)
            low = _q(entry_price - self.offset_low)
            return high, low

        if self.mode == self.MODE_PERCENT:
            high = _q(entry_price * (Decimal("1") + (self.percent_high / Decimal("100"))))
            low = _q(entry_price * (Decimal("1") - (self.percent_low / Decimal("100"))))
            return high, low

        return None
