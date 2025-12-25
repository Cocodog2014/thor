from __future__ import annotations
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone, dateparse

"""Deprecated: per-tick DB upserts replaced by Redis→flush pipeline.

This module is retained as a stub to avoid accidental double-writes to
MarketIntraday. All intraday bar creation now flows through Redis queues and
services.intraday.flush.flush_closed_bars. Remove calls to update_intraday_bars_for_country in
favor of the flush path.
"""


def update_intraday_bars_for_country(country: str, enriched_rows, twentyfour_map):
    return {'intraday_bars': 0, 'intraday_updates': 0}

