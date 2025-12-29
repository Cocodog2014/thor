from __future__ import annotations

import logging
from django.db import transaction
from django.utils import timezone

from ThorTrading.models.MarketSession import MarketSession

logger = logging.getLogger(__name__)


def _resolve_capture_group(country: str, session_number: int | None) -> int | None:
    if session_number is not None:
        return session_number
    return (
        MarketSession.objects
        .filter(country=country)
        .exclude(capture_group__isnull=True)
        .order_by("-capture_group")
        .values_list("capture_group", flat=True)
        .first()
    )


@transaction.atomic
def finalize_pending_sessions_at_close(country: str, *, capture_group: int | None = None, session_number: int | None = None) -> int:
    """
    End-of-session rule:
      - If still PENDING and NOT frozen (target_hit_at is null) -> mark NEUTRAL.
      - Never override a frozen outcome.
    """
    group = capture_group or _resolve_capture_group(country, session_number)
    if group is None:
        return 0

    qs = (
        MarketSession.objects
        .select_for_update()
        .filter(country=country, capture_group=group, wndw="PENDING", target_hit_at__isnull=True)
    )

    count = qs.count()
    if count == 0:
        return 0

    # Don't touch target_hit_* fields; we are expiring the idea.
    updated = qs.update(wndw="NEUTRAL")

    logger.info(
        "⛔ Finalize close: country=%s group=%s -> %s PENDING sessions set to NEUTRAL at %s",
        country, group, updated, timezone.now()
    )
    return updated
