"""Target High / Low Configuration Model

Provides per-symbol configurable offsets used to derive `target_high` and 
`target_low` for a `MarketSession` when market open signals are captured.

Purpose:
Different futures contracts have vastly different tick sizes, price ranges, 
and volatility profiles. This model allows admins to define custom target 
offsets per symbol using either:
- **Points mode**: Fixed absolute offsets (e.g., ES +/- 25 points)
- **Percent mode**: Percentage-based offsets (e.g., VX +/- 5%)
- **Disabled mode**: No targets calculated for that symbol

Configuration is 100% admin-driven via Django admin interface. Targets are
automatically quantized to each symbol's display precision (configured in
TradingInstrument.display_precision).

Usage Flow:
1. Admin creates one `TargetHighLowConfig` per symbol (YM, ES, NQ, RTY, etc.)
2. Selects mode: POINTS, PERCENT, or DISABLED
3. Sets offset values appropriate to that symbol's characteristics
4. Market open capture queries this config to compute targets
5. If no config exists or mode=DISABLED → targets remain None (no grading)

Target Interpretation:
- **BUY signals**: target_high = profit target, target_low = stop loss
- **SELL signals**: target_low = profit target, target_high = stop loss
- Grading logic evaluates which level hits first within the evaluation window

Precision Handling:
Computed targets respect TradingInstrument.display_precision:
- YM (display_precision=0): whole numbers (47683, 47663)
- ES (display_precision=2): two decimals (5923.25, 5898.75)
- SI (display_precision=3): three decimals (31.850, 31.350)
"""

from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError


class TargetHighLowConfig(models.Model):
    MODE_POINTS = 'POINTS'
    MODE_PERCENT = 'PERCENT'
    MODE_DISABLED = 'DISABLED'
    MODE_CHOICES = [
        (MODE_POINTS, 'Points'),
        (MODE_PERCENT, 'Percent'),
        (MODE_DISABLED, 'Disabled'),
    ]

    symbol = models.CharField(
        max_length=10,
        unique=True,
        help_text="Trading symbol (YM, ES, NQ, RTY, CL, SI, HG, GC, VX, DX, ZB)"
    )

    mode = models.CharField(
        max_length=10,
        choices=MODE_CHOICES,
        default=MODE_POINTS,
        help_text="Computation mode: Points adds/subtracts fixed amounts; Percent uses percentage offsets; Disabled skips target calculation."
    )

    # Point offsets (absolute) - optional depending on mode
    offset_high = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Absolute points above entry (BUY target / SELL stop)"
    )
    offset_low = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Absolute points below entry (BUY stop / SELL target)"
    )

    # Percent offsets (if mode=PERCENT) - expressed as percentage (e.g. 0.5 => 0.5%)
    percent_high = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent above entry (e.g. 0.50 = +0.50%)"
    )
    percent_low = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percent below entry (e.g. 0.50 = -0.50%)"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Deactivate without deleting. If inactive or disabled, capture falls back to legacy default if no other config exists."
    )

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Target High/Low Config"
        verbose_name_plural = "Target High/Low Configs"
        ordering = ["symbol"]

    def __str__(self):  # pragma: no cover
        if self.mode == self.MODE_POINTS:
            return f"{self.symbol}: +{self.offset_high} / -{self.offset_low} pts"
        if self.mode == self.MODE_PERCENT:
            return f"{self.symbol}: +{self.percent_high}% / -{self.percent_low}%"
        return f"{self.symbol}: (disabled)"

    def clean(self):
        # Ensure required fields for each mode
        if self.mode == self.MODE_POINTS:
            if self.offset_high is None or self.offset_low is None:
                raise ValidationError("Points mode requires offset_high and offset_low")
            if (self.offset_high is not None and self.offset_high <= 0) or (self.offset_low is not None and self.offset_low <= 0):
                raise ValidationError("Point offsets must be positive values (enter absolute magnitudes, no minus sign)")
        elif self.mode == self.MODE_PERCENT:
            if self.percent_high is None or self.percent_low is None:
                raise ValidationError("Percent mode requires percent_high and percent_low")
            if (self.percent_high is not None and self.percent_high <= 0) or (self.percent_low is not None and self.percent_low <= 0):
                raise ValidationError("Percent offsets must be positive (e.g. 0.50 for +0.50%)")

    def compute_targets(self, entry_price: Decimal, quant: Decimal | None = None):
        """Return (target_high, target_low) or None if disabled.

        Percent interpretation: percent_high=0.50 means +0.50% (multiply by 1.0050)

        `quant` is an optional Decimal quantization unit (e.g. Decimal('0.01')).
        If not provided, no explicit quantize is applied – the caller can decide.
        """
        if entry_price is None:
            raise ValueError("entry_price is required to compute targets")

        if not self.is_active or self.mode == self.MODE_DISABLED:
            return None

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
