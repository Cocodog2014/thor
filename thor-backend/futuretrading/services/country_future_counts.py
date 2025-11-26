"""Utilities for managing the ``country_future`` ordering column."""

from __future__ import annotations

from decimal import Decimal
import logging
from typing import Iterable, Optional

from FutureTrading.models.MarketSession import MarketSession


class CountryFutureCounter:
    """Assigns ``country_future`` counters per (country, future) pair.

    Historically this module ran a bulk recalculation after every capture which
    overwrote past values. The counter is now an append-only sequence that
    should be set exactly once—when a row is created. Moving the logic into a
    class keeps the behavior in one place so it can be reused outside
    ``MarketOpenCapture`` (tests, repair scripts, etc.).
    """

    def __init__(self, model=MarketSession):
        self.model = model
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def assign_sequence(self, session: MarketSession, *, overwrite: bool = False) -> Optional[Decimal]:
        """Ensure ``session.country_future`` has the next sequence value.

        Returns the value that was written, or ``None`` if no write occurred.
        ``overwrite`` defaults to ``False`` so we only write brand-new rows.
        Pass ``overwrite=True`` explicitly if a repair job truly needs to
        recalc historical rows.
        """
        if session is None:
            return None
        if session.country_future is not None:
            if not overwrite:
                self.logger.debug(
                    "country_future already set for id=%s (%s/%s); skipping overwrite",
                    getattr(session, "id", None),
                    getattr(session, "country", None),
                    getattr(session, "future", None),
                )
                return None
        if not session.country or not session.future:
            self.logger.warning(
                "Cannot assign country_future without both country and future (id=%s)",
                session.id,
            )
            return None

        next_value = self._next_value(session.country, session.future, exclude_id=session.id)
        session.country_future = next_value
        session.save(update_fields=["country_future"])
        self.logger.debug(
            "Assigned country_future=%s to session id=%s (%s/%s)",
            next_value,
            session.id,
            session.country,
            session.future,
        )
        return next_value

    def bulk_assign(self, sessions: Iterable[MarketSession], *, overwrite: bool = False) -> int:
        """Assign counters for each provided session, returning the number updated."""
        updated = 0
        for session in sessions:
            if self.assign_sequence(session, overwrite=overwrite) is not None:
                updated += 1
        return updated

    def _next_value(self, country: str, future: str, exclude_id: Optional[int] = None) -> Decimal:
        queryset = self.model.objects.filter(country=country, future=future)
        if exclude_id is not None:
            queryset = queryset.exclude(id=exclude_id)
        last_session = queryset.order_by('-country_future').first()
        last_value = last_session.country_future if last_session and last_session.country_future else Decimal('0')
        return last_value + Decimal('1')


__all__ = ["CountryFutureCounter"]