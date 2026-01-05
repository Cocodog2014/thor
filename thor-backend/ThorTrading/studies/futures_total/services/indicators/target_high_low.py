"""Target high/low computation service."""

from __future__ import annotations

import logging
from functools import lru_cache
from decimal import Decimal
from typing import Optional, Tuple

try:
    # Optional normalization map; tolerate missing config module.
    from ThorTrading.config.symbols import SYMBOL_NORMALIZE_MAP  # type: ignore
except Exception:  # pragma: no cover - defensive for missing file
    SYMBOL_NORMALIZE_MAP: dict[str, str] = {}
from ThorTrading.models.target_high_low import TargetHighLowConfig
from Instruments.models import Instrument
from Instruments.models.rtd import TradingInstrument

logger = logging.getLogger(__name__)


@lru_cache(maxsize=128)
def _get_quant_for_symbol(symbol: str) -> Optional[Decimal]:
    base = symbol.lstrip("/").upper()

    inst2 = Instrument.objects.filter(symbol__iexact=base, is_active=True).first()
    if inst2:
        precision = int(getattr(inst2, "display_precision", 2) or 2)
        return Decimal("1").scaleb(-precision)

    inst = (
        TradingInstrument.objects.filter(symbol__iexact=base)
        .first()
        or TradingInstrument.objects.filter(symbol__iexact=f"/{base}").first()
        or TradingInstrument.objects.filter(feed_symbol__iexact=symbol).first()
        or TradingInstrument.objects.filter(feed_symbol__iexact=f"/{base}").first()
    )

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


def compute_targets_for_symbol(*args, **kwargs) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """Compute target high/low with flexible calling conventions.

    Backward compatible:
    - compute_targets_for_symbol(symbol, entry_price)
    - compute_targets_for_symbol(country, symbol, entry_price)  # country ignored
    - compute_targets_for_symbol(symbol, entry_price, country=...)
    """

    country = kwargs.get("country")  # currently unused but accepted for compatibility

    if len(args) == 2:
        symbol, entry_price = args
    elif len(args) == 3:
        country, symbol, entry_price = args  # country positional ignored
    else:
        raise TypeError("compute_targets_for_symbol expected 2 or 3 positional arguments")

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
            return None, None

        targets = _compute_from_config(cfg, entry_price, quant=quant)
        return targets if targets else (None, None)

    except Exception as e:
        logger.error("Target compute error for %s: %s", symbol, e)
        return None, None


__all__ = ["compute_targets_for_symbol"]
