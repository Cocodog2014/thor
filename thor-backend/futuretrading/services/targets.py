"""Target high/low computation service.

Provides single helper to compute (target_high, target_low) given a symbol and entry price.
Logic order:
1. Normalize symbol using SYMBOL_NORMALIZE_MAP.
2. Look for active TargetHighLowConfig for symbol.
3. If active and compute succeeds → return config targets.
4. Else fallback to legacy ±20 band.
5. If entry_price missing → return (None, None).
"""
from __future__ import annotations
from decimal import Decimal
from typing import Tuple, Optional
import logging

from FutureTrading.constants import SYMBOL_NORMALIZE_MAP
from FutureTrading.models.target_high_low import TargetHighLowConfig

logger = logging.getLogger(__name__)

LEGACY_OFFSET = Decimal('20')  # legacy default band size


def compute_targets_for_symbol(symbol: str, entry_price: Optional[Decimal]) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    if entry_price is None:
        return None, None
    try:
        canonical = SYMBOL_NORMALIZE_MAP.get(symbol, symbol).upper()
        cfg = TargetHighLowConfig.objects.filter(symbol__iexact=canonical, is_active=True).first()
        if cfg:
            try:
                targets = cfg.compute_targets(entry_price)
                if targets:
                    high, low = targets
                    return high, low
            except Exception as e:
                logger.warning(f"Target config compute failed for {canonical}: {e}; falling back")
        # Fallback legacy
        return entry_price + LEGACY_OFFSET, entry_price - LEGACY_OFFSET
    except Exception as e:
        logger.error(f"Unexpected target compute error for {symbol}: {e}")
        return None, None

__all__ = ["compute_targets_for_symbol"]
