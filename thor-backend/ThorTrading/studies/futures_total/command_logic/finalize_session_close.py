from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from Instruments.models.market_24h import MarketTrading24Hour
from ThorTrading.studies.futures_total.models.market_session import MarketSession


def run(
    *,
    country: str,
    symbol: str,
    session_number: int | None,
    dry_run: bool,
    stdout,
    style,
) -> None:
    # Resolve target session by session_number identity
    if session_number is not None:
        session = (
            MarketSession.objects.filter(country=country, session_number=session_number)
            .order_by("-id")
            .first()
        )
        if session is None:
            raise ValueError(
                f"No MarketSession found for country={country} session_number={session_number}."
            )
        group = session_number
    else:
        session = (
            MarketSession.objects.filter(country=country)
            .order_by("-session_number", "-id")
            .first()
        )
        if session is None:
            raise ValueError(f"No MarketSession found for country={country}.")
        group = session.session_number

    try:
        twentyfour = MarketTrading24Hour.objects.get(session_group=group, symbol=symbol)
    except MarketTrading24Hour.DoesNotExist:
        raise ValueError(
            f"No MarketTrading24Hour found for session_group={group} symbol={symbol}. Supervisor must populate it first."
        )

    close_val = twentyfour.close_24h
    if close_val is None:
        raise ValueError("MarketTrading24Hour.close_24h is None; cannot finalize session close.")

    if dry_run:
        stdout.write(
            style.WARNING(
                f"Dry-run: would set MarketSession.close_24h to {close_val} for country={country} group={group} from {symbol}"
            )
        )
        return

    with transaction.atomic():
        session.close_24h = close_val
        session.captured_at = session.captured_at or timezone.now()
        session.save(update_fields=["close_24h", "captured_at"])

    stdout.write(
        style.SUCCESS(
            f"Finalized session for {country} group={group}: close_24h={close_val} from {symbol}"
        )
    )
