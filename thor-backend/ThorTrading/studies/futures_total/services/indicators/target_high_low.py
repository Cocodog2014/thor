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
from ThorTrading.studies.futures_total.models.target_high_low import TargetHighLowConfig
from Instruments.models import Instrument

logger = logging.getLogger(__name__)


@lru_cache(maxsize=128)
def _get_quant_for_symbol(symbol: str) -> Optional[Decimal]:
    base = symbol.lstrip("/").upper()

    inst2 = Instrument.objects.filter(
        symbol__in=[base, f"/{base}"],
        is_active=True,
    ).first()
    if inst2:
        precision = int(getattr(inst2, "display_precision", 2) or 2)
        return Decimal("1").scaleb(-precision)

    logger.warning("No Instrument for %s; skipping quantization.", symbol)
    return None


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

    country = kwargs.get("country")

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

        cfg_qs = TargetHighLowConfig.objects.filter(symbol__iexact=canonical, is_active=True)
        if country:
            cfg_qs = cfg_qs.filter(country__iexact=str(country))

        cfg = cfg_qs.first()

        if not cfg:
            return None, None

        targets = _compute_from_config(cfg, entry_price, quant=quant)
        return targets if targets else (None, None)

    except Exception as e:
        logger.error("Target compute error for %s: %s", symbol, e)
        return None, None


__all__ = ["compute_targets_for_symbol"]
