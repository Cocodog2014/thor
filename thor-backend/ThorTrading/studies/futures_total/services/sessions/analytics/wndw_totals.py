"""Snapshot totals for ``country_symbol_wndw_total`` at capture time."""
from __future__ import annotations

import logging
from typing import Dict, Iterable, Optional

from django.db.models import Q

from ThorTrading.studies.futures_total.models.market_session import MarketSession


class CountrySymbolWndwTotalsService:
    """Computes historical signal/outcome totals for a (country, symbol) pair."""

    SIGNAL_KEYS = (
        "STRONG_BUY",
        "BUY",
        "HOLD",
        "SELL",
        "STRONG_SELL",
    )

    OUTCOME_KEYS = {
        "WORKED": "worked",
        "DIDNT_WORK": "didnt_work",
        "NEUTRAL": "neutral",
        "PENDING": "pending",
    }

    def __init__(self, model=MarketSession):
        self.model = model
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def update_for_session_number(self, session_number: int, country: str) -> int:
        """Populate snapshots for all new rows in a session_number."""
        if session_number in (None, "") or not country:
            self.logger.warning(
                "update_for_session_number requires session_number and country; nothing to do.",
            )
            return 0

        pending_rows = (
            self.model.objects.filter(
                session_number=session_number,
                country=country,
            ).filter(Q(country_symbol_wndw_total__isnull=True) | Q(country_symbol_wndw_total=0))
        )

        if not pending_rows.exists():
            self.logger.info(
                "No pending MarketSession rows found for session_number %s and country %s; nothing to update.",
                session_number,
                country,
            )
            return 0

        updated = 0
        for row in pending_rows:
            summary = self._build_summary_for_row(row)
            total_value = summary["total_records"]
            row.country_symbol_wndw_total = total_value
            row.save(update_fields=["country_symbol_wndw_total"])
            updated += 1
            self.logger.debug(
                "WNDW totals snapshot id=%s (%s/%s) -> %s",
                row.id,
                row.country,
                row.symbol,
                total_value,
            )

        self.logger.info(
            "Set %s WNDW snapshots for session_number %s, country %s.",
            updated,
            session_number,
            country,
        )
        return updated

    def _build_summary_for_row(self, row) -> Dict[str, int]:
        summary = self._empty_summary()
        for record in self._historical_rows(row):
            signal_key = self._normalize_signal(record.get("bhs"))
            outcome_key = self._normalize_outcome(record.get("wndw"))

            if signal_key:
                summary[signal_key] += 1
                if outcome_key == "worked":
                    summary[f"{signal_key}_worked"] += 1
                elif outcome_key == "didnt_work":
                    summary[f"{signal_key}_didnt_work"] += 1

            summary["total_records"] += 1
            if outcome_key:
                summary[f"{outcome_key}_total"] += 1

        return summary

    def _historical_rows(self, row) -> Iterable[Dict[str, Optional[str]]]:
        return (
            self.model.objects
            .filter(country=row.country, symbol=row.symbol, captured_at__lte=row.captured_at)
            .order_by("captured_at")
            .values("bhs", "wndw")
        )

    def _empty_summary(self) -> Dict[str, int]:
        summary: Dict[str, int] = {
            "total_records": 0,
            "worked_total": 0,
            "didnt_work_total": 0,
            "neutral_total": 0,
            "pending_total": 0,
        }
        for signal in self.SIGNAL_KEYS:
            key = signal.lower()
            summary[key] = 0
            summary[f"{key}_worked"] = 0
            summary[f"{key}_didnt_work"] = 0
        return summary

    def _normalize_signal(self, raw_signal: Optional[str]) -> Optional[str]:
        if not raw_signal:
            return None
        upper = raw_signal.upper()
        if upper in self.SIGNAL_KEYS:
            return upper.lower()
        return None

    def _normalize_outcome(self, raw_outcome: Optional[str]) -> Optional[str]:
        if not raw_outcome:
            return None
        upper = raw_outcome.upper()
        return self.OUTCOME_KEYS.get(upper)


_service = CountrySymbolWndwTotalsService()


def update_country_symbol_wndw_total(session_number: int, country: str) -> int:
    """Wrapper around the service."""
    return _service.update_for_session_number(session_number=session_number, country=country)


def update_country_future_wndw_total(session_number: int, country: str) -> int:  # Backward compatibility
    return update_country_symbol_wndw_total(session_number=session_number, country=country)


__all__ = [
    "CountrySymbolWndwTotalsService",
    "update_country_symbol_wndw_total",
    "update_country_future_wndw_total",
]
