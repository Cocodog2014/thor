
"""
Target high/low computation service.

Single source of truth for how we derive (target_high, target_low)
for a given symbol + entry price.

Configuration is 100% admin-driven:

* Per-instrument decimals:
  - TradingInstrument.display_precision (set in admin)
* Per-instrument target offsets:
  - TargetHighLowConfig (mode, offset_high/low, percent_high/low)

Behavior:
- If there is an active TargetHighLowConfig for the symbol, we use it.
- If there is NO config, or it's disabled, we return (None, None).
- No legacy ±20 fallback is used.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional, Tuple

from FutureTrading.constants import SYMBOL_NORMALIZE_MAP
from FutureTrading.models.target_high_low import TargetHighLowConfig
from FutureTrading.models import TradingInstrument

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_quant_for_symbol(symbol: str) -> Optional[Decimal]:
    """
    Use TradingInstrument.display_precision (admin-set)
    to build a quantizer such as:

        precision = 0  -> Decimal('1')
        precision = 2  -> Decimal('0.01')
        precision = 3  -> Decimal('0.001')

    Returns:
        Decimal quantization unit, or None if no TradingInstrument exists.
    """
    base = symbol.lstrip("/").upper()

    inst = TradingInstrument.objects.filter(
        symbol__in=[base, f"/{base}"]
    ).first()

    if not inst:
        logger.warning("No TradingInstrument for %s; skipping quantization.", symbol)
        return None

    precision = inst.display_precision
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

    def _q(v: Decimal) -> Decimal:
        return v.quantize(quant) if quant is not None else v

    if cfg.mode == cfg.MODE_POINTS:
        high = _q(entry_price + cfg.offset_high)
        low = _q(entry_price - cfg.offset_low)
        return high, low

    if cfg.mode == cfg.MODE_PERCENT:
        up = entry_price * (Decimal("1") + (cfg.percent_high / Decimal("100")))
        dn = entry_price * (Decimal("1") - (cfg.percent_low / Decimal("100")))
        return _q(up), _q(dn)

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

    No fallback bands. If a config does not exist or is disabled:
    → return (None, None)
    → MarketOpenCapture will store null targets.
    """
    if entry_price is None:
        return None, None

    try:
        canonical = SYMBOL_NORMALIZE_MAP.get(symbol, symbol).lstrip("/").upper()

        quant = _get_quant_for_symbol(canonical)

        cfg = TargetHighLowConfig.objects.filter(
            symbol__iexact=canonical,
            is_active=True,
        ).first()

        if not cfg:
            # No admin config = no targets
            return None, None

        targets = _compute_from_config(cfg, entry_price, quant=quant)
        return targets if targets else (None, None)

    except Exception as e:
        logger.error("Target compute error for %s: %s", symbol, e)
        return None, None


__all__ = ["compute_targets_for_symbol"]
