# FutureTrading/services/country_future_wndw_counts.py

"""
Per-market WNDW totals for MarketSession rows.

Requirement:
  For each newly created MarketSession row, compute `country_future_wndw_total` 
  by aggregating WNDW outcomes (WORKED/DIDNT_WORK) from all PREVIOUS rows 
  for that (country, future) pair. This is a frozen snapshot - once written,
  it never changes even when future sessions are added.

Implementation:
  Called right after market open capture. For each new row, count historical
  WNDW outcomes and store the aggregate. Never updates old rows.
"""

from typing import Optional
import logging
from decimal import Decimal

from FutureTrading.models.MarketSession import MarketSession


logger = logging.getLogger(__name__)


def update_country_future_wndw_total(
    session_number: int,
    country: str,
    window_size: Optional[int] = None,
) -> None:
    """
    Update country_future_wndw_total for NEW rows created in a specific session.

    For each new row:
    1. Query all PREVIOUS rows for same (country, future) where captured_at < current
    2. Count WNDW outcomes: WORKED, DIDNT_WORK, etc.
    3. Store aggregate as snapshot - never update this row again
    
    IMPORTANT: Only updates rows where country_future_wndw_total is NULL.
    Once set, the value is frozen forever (historical snapshot).
    """
    if not session_number or not country:
        logger.warning(
            "update_country_future_wndw_total requires session_number and country; nothing to do."
        )
        return

    # Only update NEW rows that don't have a value yet
    current_rows = MarketSession.objects.filter(
        session_number=session_number,
        country=country,
        country_future_wndw_total__isnull=True,  # Only rows without a value
    )

    if not current_rows.exists():
        logger.info(
            "No new MarketSession rows found for session %s and country %s; nothing to update.",
            session_number,
            country,
        )
        return

    updated = 0
    for row in current_rows:
        # Get all PREVIOUS rows for this (country, future) pair
        # captured_at < current row ensures we only look at history
        historical_rows = MarketSession.objects.filter(
            country=row.country,
            future=row.future,
            captured_at__lt=row.captured_at,
        )
        
        # Count WNDW outcomes from history
        worked_count = historical_rows.filter(wndw='WORKED').count()
        didnt_work_count = historical_rows.filter(wndw='DIDNT_WORK').count()
        neutral_count = historical_rows.filter(wndw='NEUTRAL').count()
        pending_count = historical_rows.filter(wndw='PENDING').count()
        
        # Calculate total - using worked count as the primary metric
        # You can adjust this formula based on what you want to track
        total_value = Decimal(worked_count)
        
        # Set the value - this is a one-time write, never updated again
        row.country_future_wndw_total = total_value
        row.save(update_fields=["country_future_wndw_total"])
        
        updated += 1
        logger.debug(
            "WNDW snapshot id=%s (%s/%s) -> %s (W:%s DW:%s N:%s P:%s)",
            row.id,
            row.country,
            row.future,
            total_value,
            worked_count,
            didnt_work_count,
            neutral_count,
            pending_count,
        )

    logger.info(
        "Set WNDW snapshots for session %s, country %s on %s new rows.",
        session_number,
        country,
        updated,
    )
