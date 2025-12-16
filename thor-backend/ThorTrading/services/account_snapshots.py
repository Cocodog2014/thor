"""Helpers to trigger account snapshot commands from Thor services."""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional, Union

from django.core.management import call_command

logger = logging.getLogger(__name__)

DateLike = Union[date, str]


def _format_trading_date(value: Optional[DateLike]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def trigger_account_daily_snapshots(
    *,
    trading_date: Optional[DateLike] = None,
    broker: str = "ALL",
    source: str = "AUTO",
    overwrite: bool = False,
) -> bool:
    """Run the snapshot management command and log the outcome."""

    options = {
        "broker": broker,
        "source": source,
        "overwrite": overwrite,
    }
    formatted_date = _format_trading_date(trading_date)
    if formatted_date:
        options["trading_date"] = formatted_date

    try:
        logger.info(
            "Running snapshot_eod_balances broker=%s source=%s date=%s overwrite=%s",
            broker,
            source,
            formatted_date,
            overwrite,
        )
        call_command("snapshot_eod_balances", **options)
        logger.info("snapshot_eod_balances completed successfully")
        return True
    except Exception:
        logger.exception("snapshot_eod_balances command failed")
        return False


__all__ = ["trigger_account_daily_snapshots"]
