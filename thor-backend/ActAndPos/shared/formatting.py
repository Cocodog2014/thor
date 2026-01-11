from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def format_money(value: Decimal | int | float | str | None) -> str:
    """Format a money-like value to a 2-decimal string.

    Contract: always returns a plain numeric string like "12.34" (no $ sign, no commas).
    """

    if value is None:
        return "0.00"
    dec = _to_decimal(value)
    return str(dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def format_pct(value: Decimal | int | float | str | None) -> str:
    """Format a percent-like value to a 2-decimal string.

    Contract: always returns a plain numeric string like "1.23" (no % sign).

    Note: caller owns scaling. If you want "1.23" for 1.23%, pass 1.23.
    If you want "1.23" for 0.0123, multiply by 100 before calling.
    """

    if value is None:
        return "0.00"
    dec = _to_decimal(value)
    return str(dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
