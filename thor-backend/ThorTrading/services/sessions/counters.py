"""Session-domain counters and sequencing helpers."""
from __future__ import annotations

from decimal import Decimal
import logging
from typing import Iterable, Optional

from ThorTrading.models.MarketSession import MarketSession


class CountrySymbolCounter:
    """Assigns ``country_symbol`` counters per (country, symbol) pair.

    Append-only sequence; set on row creation, optionally repair with overwrite.
    """

    def __init__(self, model=MarketSession):
        self.model = model
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def assign_sequence(self, session: MarketSession, *, overwrite: bool = False) -> Optional[Decimal]:
        """Ensure ``session.country_symbol`` has the next sequence value."""
        if session is None:
            return None
        if session.country_symbol is not None:
            if not overwrite:
                self.logger.debug(
                    "country_symbol already set for id=%s (%s/%s); skipping overwrite",
                    getattr(session, "id", None),
                    getattr(session, "country", None),
                    getattr(session, "symbol", None),
                )
                return None
        if not session.country or not session.symbol:
            self.logger.warning(
                "Cannot assign country_symbol without both country and symbol (id=%s)",
                session.id,
            )
            return None

        next_value = self._next_value(session.country, session.symbol, exclude_id=session.id)
        session.country_symbol = next_value
        session.save(update_fields=["country_symbol"])
        self.logger.debug(
            "Assigned country_symbol=%s to session id=%s (%s/%s)",
            next_value,
            session.id,
            session.country,
            session.symbol,
        )
        return next_value

    def bulk_assign(self, sessions: Iterable[MarketSession], *, overwrite: bool = False) -> int:
        """Assign counters for each provided session, returning the number updated."""
        updated = 0
        for session in sessions:
            if self.assign_sequence(session, overwrite=overwrite) is not None:
                updated += 1
        return updated

    def _next_value(self, country: str, symbol: str, exclude_id: Optional[int] = None) -> Decimal:
        queryset = self.model.objects.filter(country=country, symbol=symbol).exclude(country_symbol__isnull=True)
        if exclude_id is not None:
            queryset = queryset.exclude(id=exclude_id)
        last_session = queryset.order_by('-country_symbol').first()
        last_value = last_session.country_symbol if last_session and last_session.country_symbol else Decimal('0')
        return last_value + Decimal('1')


__all__ = ["CountrySymbolCounter"]
