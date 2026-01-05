"""DB-only classification & weighting logic.

No hardcoded fallback maps.
All thresholds/weights come from admin-managed models:
- SignalStatValue (per instrument + signal threshold)
- ContractWeight (per instrument weight; can be negative to invert)
- SignalWeight (per signal contribution weight)
"""

from __future__ import annotations

import logging
from decimal import Decimal
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from ThorTrading.studies.futures_total.models.rtd import ContractWeight, SignalStatValue, SignalWeight

logger = logging.getLogger(__name__)

SIGNAL_ORDER = ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]


def _normalize_symbol(symbol: str) -> str:
    # No hardcoded maps. Normalize consistently.
    return (symbol or "").strip().lstrip("/").upper()


@lru_cache(maxsize=512)
def _stat_thresholds(symbol: str) -> dict[str, Decimal]:
    """Return thresholds for STRONG_BUY/BUY/SELL/STRONG_SELL from DB for this symbol."""
    normalized = _normalize_symbol(symbol)

    qs = SignalStatValue.objects.filter(instrument__symbol__in=[normalized, f"/{normalized}"])
    out: dict[str, Decimal] = {}
    for row in qs:
        try:
            out[str(row.signal)] = Decimal(str(row.value))
        except Exception:
            continue

    # Require the four thresholds needed by classify()
    required = {"STRONG_BUY", "BUY", "SELL", "STRONG_SELL"}
    if not required.issubset(out.keys()):
        missing = sorted(required - set(out.keys()))
        logger.warning(
            "SignalStatValue missing for %s: %s (classification disabled for this symbol)",
            normalized,
            missing,
        )
        return {}
    return out


@lru_cache(maxsize=512)
def _contract_weight(symbol: str) -> Decimal:
    normalized = _normalize_symbol(symbol)
    try:
        cw = ContractWeight.objects.get(instrument__symbol__in=[normalized, f"/{normalized}"])
        return Decimal(str(cw.weight))
    except ContractWeight.DoesNotExist:
        logger.warning(
            "ContractWeight missing for %s (defaulting to 0 => excluded from composite)",
            normalized,
        )
        return Decimal("0")


@lru_cache(maxsize=64)
def _signal_weight(signal: str) -> int:
    try:
        sw = SignalWeight.objects.get(signal=signal)
        return int(sw.weight)
    except SignalWeight.DoesNotExist:
        logger.warning("SignalWeight missing for signal=%s (defaulting to 0)", signal)
        return 0


def classify(
    symbol: str, net_change: Optional[Decimal | float | int | str]
) -> Tuple[Optional[str], Optional[Decimal], Decimal, int]:
    """Returns: (signal, stat_value, contract_weight, signal_weight).

    Where stat_value is the threshold value for the chosen signal (for composite display/logic).
    """
    weight = _contract_weight(symbol)
    if net_change is None:
        return None, None, weight, 0

    try:
        change = Decimal(str(net_change))
    except Exception:
        return None, None, weight, 0

    thresholds = _stat_thresholds(symbol)
    if not thresholds:
        # Admin not configured for this symbol
        return None, None, weight, 0

    strong_buy = thresholds["STRONG_BUY"]
    buy = thresholds["BUY"]
    sell = thresholds["SELL"]
    strong_sell = thresholds["STRONG_SELL"]

    if change > strong_buy:
        signal = "STRONG_BUY"
    elif change > buy:
        signal = "BUY"
    elif change >= sell:
        signal = "HOLD"
    elif change > strong_sell:
        signal = "SELL"
    else:
        signal = "STRONG_SELL"

    # Use DB-controlled signal weight; instrument inversion happens via ContractWeight being negative (admin-controlled)
    sig_weight = _signal_weight(signal)

    return signal, thresholds.get(signal), weight, sig_weight


def enrich_quote_row(row: dict) -> dict:
    """Adds extended_data:
      - signal
      - stat_value
      - contract_weight
      - signal_weight
    """
    instrument = row.get("instrument", {}) or {}
    symbol = instrument.get("symbol") or row.get("symbol") or ""
    extended = row.setdefault("extended_data", {})

    if not extended.get("signal"):
        change_raw = row.get("change")
        signal, stat_value, contract_weight, signal_weight = classify(symbol, change_raw)

        if signal:
            extended["signal"] = signal
        if stat_value is not None:
            extended["stat_value"] = str(stat_value)
        extended["contract_weight"] = str(contract_weight)
        extended["signal_weight"] = str(signal_weight)
    else:
        # If someone prefilled signal, still ensure weights come from DB only.
        if "contract_weight" not in extended:
            extended["contract_weight"] = str(_contract_weight(symbol))
        if "signal_weight" not in extended:
            existing_signal = extended.get("signal")
            extended["signal_weight"] = str(_signal_weight(existing_signal)) if existing_signal else "0"

    return row


@lru_cache(maxsize=8)
def _load_signal_weights() -> Dict[str, int]:
    """DB is the source of truth.

    Returns {signal_name: weight_int}
    """
    weights: Dict[str, int] = {}
    for row in SignalWeight.objects.all():
        try:
            weights[str(row.signal)] = int(row.weight)
        except Exception:
            continue
    if not weights:
        logger.warning("No SignalWeight rows found; composite will be empty/neutral.")
    return weights


def compute_composite(rows: List[dict]) -> dict:
    """Composite built ONLY from admin-configured values.

    - each row must have extended_data: signal, contract_weight, signal_weight
    - signal weights come from DB (SignalWeight)
    - instrument inversion can be done by setting ContractWeight negative in admin

    Returns a dict that your UI/services can consume.
    """
    if not rows:
        return {}

    # Make sure rows are enriched (adds extended_data)
    enriched = [enrich_quote_row(r) for r in rows]

    num = Decimal("0")
    den = Decimal("0")

    contributions: Dict[str, dict] = {}

    for r in enriched:
        instrument = r.get("instrument") or {}
        symbol = (instrument.get("symbol") or r.get("symbol") or "").strip()

        ext = r.get("extended_data") or {}

        try:
            cw = Decimal(str(ext.get("contract_weight", "0")))
        except Exception:
            cw = Decimal("0")

        try:
            sw = Decimal(str(ext.get("signal_weight", "0")))
        except Exception:
            sw = Decimal("0")

        if cw == 0:
            continue

        # weighted contribution
        num += cw * sw
        den += abs(cw)

        contributions[symbol] = {
            "contract_weight": str(cw),
            "signal_weight": str(sw),
            "signal": ext.get("signal"),
        }

    score = (num / den) if den != 0 else Decimal("0")

    # Pick composite signal by closest SignalWeight — zero hardcoding.
    sw_map = _load_signal_weights()
    composite_signal = None
    if sw_map:
        composite_signal = min(sw_map.items(), key=lambda kv: abs(Decimal(kv[1]) - score))[0]

    return {
        "score": float(score),
        "signal": composite_signal,
        "denominator": float(den),
        "contributions": contributions,
    }


__all__ = [
    "classify",
    "enrich_quote_row",
    "compute_composite",
]
