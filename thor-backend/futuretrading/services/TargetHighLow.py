"""Target high/low computation service.

Provides helper to compute (target_high, target_low) given a symbol and entry price.
Precision is controlled by TradingInstrument.display_precision (admin-configurable).

Logic order:
1. Normalize symbol using SYMBOL_NORMALIZE_MAP.
2. Look up TradingInstrument.display_precision to build quantization unit.
3. Look for active TargetHighLowConfig for symbol.
4. If active and compute succeeds → return config targets.
5. Else fallback to legacy ±20 band.
6. If entry_price missing → return (None, None).
"""
from __future__ import annotations
"""
Target high/low computation service.

Single source of truth for how we derive (target_high, target_low)
for a given symbol + entry price.

Configuration is 100% admin-driven:

* Per-instrument decimals:
  - TradingInstrument.display_precision  (set in admin)
* Per-instrument target offsets:
  - TargetHighLowConfig (mode, offset_high/low, percent_high/low)

Logic order:
1. Normalize symbol using SYMBOL_NORMALIZE_MAP.
2. Look up TradingInstrument.display_precision to build a quantization unit.
3. Look up active TargetHighLowConfig for the canonical symbol.
4. If config exists and compute succeeds → return those targets.
5. Else, fall back to legacy ±20 band (still quantized if we know precision).
6. If entry_price is missing → return (None, None).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional, Tuple

from FutureTrading.constants import SYMBOL_NORMALIZE_MAP
from FutureTrading.models.target_high_low import TargetHighLowConfig
from FutureTrading.models import TradingInstrument

logger = logging.getLogger(__name__)

# Legacy band used when no config exists or config fails
LEGACY_OFFSET = Decimal("20")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_quant_for_symbol(symbol: str) -> Optional[Decimal]:
    """
    Look up TradingInstrument.display_precision (configured in admin)
    and build a quantization unit Decimal, e.g.:

        precision = 0  -> Decimal('1')
        precision = 2  -> Decimal('0.01')
        precision = 3  -> Decimal('0.001')

    Returns:
        Decimal quantization unit, or None if instrument not found
        (meaning: don't quantize in this function).
    """
    base = symbol.lstrip("/").upper()

    inst = TradingInstrument.objects.filter(
        symbol__in=[base, f"/{base}"]
    ).first()

    if not inst:
        logger.warning(
            "No TradingInstrument found for symbol %s; skipping quantization",
            symbol,
        )
        return None

    precision = inst.display_precision
    # scaleb(-precision) gives 10**(-precision)
    return Decimal("1").scaleb(-precision)


def _compute_from_config(
    cfg: TargetHighLowConfig,
    entry_price: Decimal,
    quant: Optional[Decimal],
) -> Optional[Tuple[Decimal, Decimal]]:
    """
    Apply a TargetHighLowConfig to an entry price, respecting optional quant.

    Returns:
        (high, low) or None if config is inactive/disabled.
    """
    if not cfg.is_active or cfg.mode == cfg.MODE_DISABLED:
        return None

    def _q(val: Decimal) -> Decimal:
        return val.quantize(quant) if quant is not None else val

    if cfg.mode == cfg.MODE_POINTS:
        # absolute offsets in points
        high = _q(entry_price + cfg.offset_high)
        low = _q(entry_price - cfg.offset_low)
        return high, low

    if cfg.mode == cfg.MODE_PERCENT:
        # percent offsets, e.g. 0.50 => +0.50%
        high = _q(entry_price * (Decimal("1") + (cfg.percent_high / Decimal("100"))))
        low = _q(entry_price * (Decimal("1") - (cfg.percent_low / Decimal("100"))))
        return high, low

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_targets_for_symbol(
    symbol: str,
    entry_price: Optional[Decimal],
) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """
    Compute (target_high, target_low) for a symbol + entry price.

    Called by MarketOpenCapture after it decides entry_price
    (Ask for BUY, Bid for SELL).

    Returns:
        (target_high, target_low), each possibly None.
    """
    if entry_price is None:
        return None, None

    try:
        # Normalize to canonical symbol, e.g. '/ES' -> 'ES'
        canonical = SYMBOL_NORMALIZE_MAP.get(symbol, symbol).lstrip("/").upper()

        # Determine quantization based on TradingInstrument.display_precision
        quant = _get_quant_for_symbol(canonical)

        # Try to apply configured targets first
        cfg = TargetHighLowConfig.objects.filter(
            symbol__iexact=canonical,
            is_active=True,
        ).first()

        if cfg:
            try:
                targets = _compute_from_config(cfg, entry_price, quant=quant)
                if targets:
                    high, low = targets
                    return high, low
            except Exception as e:
                logger.warning(
                    "Target config compute failed for %s: %s; falling back to legacy",
                    canonical,
                    e,
                )

        # Fallback legacy: ±20 points
        high = entry_price + LEGACY_OFFSET
        low = entry_price - LEGACY_OFFSET

        if quant is not None:
            high = high.quantize(quant)
            low = low.quantize(quant)

        return high, low

    except Exception as e:
        logger.error("Unexpected target compute error for %s: %s", symbol, e)
        return None, None


__all__ = ["compute_targets_for_symbol"]
