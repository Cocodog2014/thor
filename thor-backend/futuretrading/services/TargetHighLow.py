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
from decimal import Decimal
from typing import Tuple, Optional
import logging

from FutureTrading.constants import SYMBOL_NORMALIZE_MAP
from FutureTrading.models.target_high_low import TargetHighLowConfig
from FutureTrading.models import TradingInstrument

logger = logging.getLogger(__name__)

LEGACY_OFFSET = Decimal('20')  # legacy default band size


def _get_quant_for_symbol(symbol: str) -> Decimal | None:
    """
    Look up TradingInstrument.display_precision (configured in admin)
    and build a quantization unit Decimal, e.g. precision=2 -> Decimal('0.01').

    Returns None if instrument is missing, meaning: 'don't quantize here'.
    """
    base = symbol.lstrip('/').upper()
    inst = TradingInstrument.objects.filter(
        symbol__in=[base, f'/{base}']
    ).first()

    if not inst:
        logger.warning("No TradingInstrument found for symbol %s; skipping quantization", symbol)
        return None

    precision = inst.display_precision
    # Example: precision=0 -> Decimal('1'), precision=2 -> Decimal('0.01'), precision=3 -> '0.001'
    return Decimal('1').scaleb(-precision)


def compute_targets_for_symbol(symbol: str, entry_price: Optional[Decimal]) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """
    Compute (target_high, target_low) for a symbol using:

    - TargetHighLowConfig (admin-configurable offsets)
    - TradingInstrument.display_precision (admin-configurable decimals)

    No per-symbol decimals are hard-coded here: it's all driven by the DB.
    """
    if entry_price is None:
        return None, None
    try:
        # Normalize and strip any leading slash so '/ES' and 'ES' both resolve
        canonical = SYMBOL_NORMALIZE_MAP.get(symbol, symbol).lstrip('/').upper()
        quant = _get_quant_for_symbol(canonical)
        
        cfg = TargetHighLowConfig.objects.filter(symbol__iexact=canonical, is_active=True).first()
        if cfg:
            try:
                targets = cfg.compute_targets(entry_price, quant=quant)
                if targets:
                    high, low = targets
                    return high, low
            except Exception as e:
                logger.warning(f"Target config compute failed for {canonical}: {e}; falling back")
        
        # Fallback legacy: +/-20 points, still respecting quantization if we have it
        high = entry_price + LEGACY_OFFSET
        low = entry_price - LEGACY_OFFSET

        if quant is not None:
            high = high.quantize(quant)
            low = low.quantize(quant)

        return high, low
    except Exception as e:
        logger.error(f"Unexpected target compute error for {symbol}: {e}")
        return None, None

__all__ = ["compute_targets_for_symbol"]
