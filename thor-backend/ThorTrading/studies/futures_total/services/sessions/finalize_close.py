from __future__ import annotations

import logging
from django.db import transaction
from django.utils import timezone

from ThorTrading.studies.futures_total.models.market_session import MarketSession

logger = logging.getLogger(__name__)


def _resolve_session_number(country: str, session_number: int | None) -> int | None:
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
def finalize_pending_sessions_at_close(country: str, *, session_number: int | None = None) -> int:
    """
    End-of-session rule:
      - If still PENDING and NOT frozen (target_hit_at is null) -> mark NEUTRAL.
      - Never override a frozen outcome.
    """
    resolved_session_number = _resolve_session_number(country, session_number)
    if resolved_session_number is None:
        return 0

    qs = (
        MarketSession.objects
        .select_for_update()
        .filter(country=country, session_number=resolved_session_number, wndw="PENDING", target_hit_at__isnull=True)
    )

    count = qs.count()
    if count == 0:
        return 0

    # Don't touch target_hit_* fields; we are expiring the idea.
    updated = qs.update(wndw="NEUTRAL")

    logger.info(
        "⛔ Finalize close: country=%s session_number=%s -> %s PENDING sessions set to NEUTRAL at %s",
        country, resolved_session_number, updated, timezone.now()
    )
    return updated
