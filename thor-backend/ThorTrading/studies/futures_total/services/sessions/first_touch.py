from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from ThorTrading.studies.futures_total.models.market_session import MarketSession

logger = logging.getLogger(__name__)


def _safe_decimal(x) -> Optional[Decimal]:
    if x in (None, "", " "):
        return None
    try:
        return Decimal(str(x))
    except Exception:
        return None


def _resolve_session_number(country: str, session_number: int | None) -> Optional[int]:
    if session_number is not None:
        return session_number
    return (
        MarketSession.objects
        .filter(country=country)
        .order_by("-session_number")
        .values_list("session_number", flat=True)
        .first()
    )


@transaction.atomic
def maybe_freeze_first_touch(
    *,
    country: str,
    symbol: str,
    bid: Optional[Decimal],
    ask: Optional[Decimal],
    tick_ts=None,
    session_number: int | None = None,
) -> bool:
    """
    First-touch wins (1-second resolution):
      - BUY uses bid (exit)
      - SELL uses ask (exit)

    If hit, freeze:
      target_hit_at, target_hit_price, target_hit_type, wndw
    Returns True if a freeze occurred.
    """
    symbol = symbol.lstrip("/").upper()

    resolved_session_number = _resolve_session_number(country, session_number)
    if resolved_session_number is None:
        return False

    session = (
        MarketSession.objects
        .select_for_update()
        .filter(country=country, session_number=resolved_session_number, symbol=symbol, wndw="PENDING")
        .first()
    )
    if not session:
        return False

    # Already frozen?
    if session.target_hit_at is not None:
        return False

    if not session.entry_price or not session.target_high or not session.target_low:
        return False

    if session.bhs in ("HOLD", None, ""):
        return False

    # Choose the evaluation price like your grader does:
    # BUY evaluates bid, SELL evaluates ask
    if session.bhs in ("BUY", "STRONG_BUY"):
        price = bid
        if price is None:
            return False
        hit_target = price >= session.target_high
        hit_stop = price <= session.target_low
        if not (hit_target or hit_stop):
            return False
        hit_type = "TARGET" if hit_target else "STOP"
        wndw = "WORKED" if hit_target else "DIDNT_WORK"

    elif session.bhs in ("SELL", "STRONG_SELL"):
        price = ask
        if price is None:
            return False
        # For SELL: target is low, stop is high
        hit_target = price <= session.target_low
        hit_stop = price >= session.target_high
        if not (hit_target or hit_stop):
            return False
        hit_type = "TARGET" if hit_target else "STOP"
        wndw = "WORKED" if hit_target else "DIDNT_WORK"

    else:
        return False

    now = timezone.now()
    session.target_hit_at = now
    session.target_hit_price = price
    session.target_hit_type = hit_type
    session.wndw = wndw

    session.save(update_fields=["target_hit_at", "target_hit_price", "target_hit_type", "wndw"])

    logger.info(
        "FIRST TOUCH FREEZE: %s %s session_number=%s hit=%s price=%s wndw=%s",
        country, symbol, resolved_session_number, hit_type, price, wndw,
    )
    return True
