# FutureTrading/services/country_future_wndw_counts.py

"""
Per-market WNDW totals for MarketSession rows.

Requirement:
  For each newly created MarketSession row, set `country_future_wndw_total` to
  the count of prior occurrences for the SAME (country, future) only — never
  mixing other countries.

Implementation:
  This function is called right after a market's open capture, with the
  specific session_number and country. It updates ONLY the rows created for
  that session + country, counting occurrences within that country.
"""

from typing import Optional
import logging

from FutureTrading.models.MarketSession import MarketSession


logger = logging.getLogger(__name__)


def update_country_future_wndw_total(
    session_number: int,
    country: str,
    window_size: Optional[int] = None,
) -> None:
    """
    Update country_future_wndw_total for rows created in a specific session
    and a specific market (country).

    Behavior:
    - Only rows where session_number = given session AND country = given
      country are updated.
    - For each updated row, the value is set to the count of rows that share
      the SAME (country, future) within this table.
    - If `window_size` is provided, restrict the count to that rolling window
      of session_numbers (inclusive). Otherwise, count across all history for
      that country.
    """
    if not session_number or not country:
        logger.warning(
            "update_country_future_wndw_total requires session_number and country; nothing to do."
        )
        return

    # The current session rows to update
    current_rows = MarketSession.objects.filter(
        session_number=session_number,
        country=country,
    )

    if not current_rows.exists():
        logger.info(
            "No MarketSession rows found for session %s and country %s; nothing to update.",
            session_number,
            country,
        )
        return

    # Base queryset for counting occurrences for this country
    if window_size is not None and window_size > 0:
        min_session = max(1, session_number - window_size + 1)
        base_qs = MarketSession.objects.filter(
            country=country,
            session_number__gte=min_session,
            session_number__lte=session_number,
        )
    else:
        base_qs = MarketSession.objects.filter(country=country)

    updated = 0
    for row in current_rows:
        total_for_pair = base_qs.filter(future=row.future).count()
        if row.country_future_wndw_total != total_for_pair:
            row.country_future_wndw_total = total_for_pair
            row.save(update_fields=["country_future_wndw_total"])
        updated += 1
        logger.debug(
            "WNDW total id=%s (%s/%s) -> %s",
            row.id,
            row.country,
            row.future,
            total_for_pair,
        )

    logger.info(
        "Updated WNDW totals for session %s, country %s on %s rows.",
        session_number,
        country,
        updated,
    )
