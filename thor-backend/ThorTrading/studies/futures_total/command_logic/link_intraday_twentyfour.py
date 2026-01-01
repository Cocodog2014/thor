from __future__ import annotations

from typing import Dict, Tuple

from django.db import transaction

from ThorTrading.models.Market24h import MarketTrading24Hour
from ThorTrading.models.MarketIntraDay import MarketIntraday
from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.services.config.country_codes import normalize_country_code


def run(
    *,
    batch_size: int,
    max_rows: int | None,
    dry_run: bool,
    create_missing: bool,
    verbose: bool,
    stdout,
    style,
) -> None:
    qs = MarketIntraday.objects.filter(twentyfour__isnull=True).order_by("id")
    if max_rows:
        qs = qs[:max_rows]

    processed = 0
    linked = 0
    skipped_missing_parent = 0
    session_group_cache: Dict[str, int | None] = {}
    twentyfour_cache: Dict[Tuple[int, str], MarketTrading24Hour | None] = {}

    def resolve_session_group(country: str) -> int | None:
        if country in session_group_cache:
            return session_group_cache[country]
        sg = (
            MarketSession.objects.filter(country=country)
            .order_by("-session_number")
            .values_list("session_number", flat=True)
            .first()
        )
        session_group_cache[country] = sg
        return sg

    def flush_buffer(rows) -> None:
        if not rows:
            return
        if dry_run:
            return
        with transaction.atomic():
            MarketIntraday.objects.bulk_update(rows, ["twentyfour"])

    buffer = []

    for row in qs.iterator(chunk_size=batch_size):
        processed += 1
        country = normalize_country_code(row.country) or row.country
        symbol = (row.symbol or "").upper()
        if not symbol:
            continue

        sg = resolve_session_group(country)
        if sg is None:
            continue

        cache_key = (sg, symbol)
        twentyfour = twentyfour_cache.get(cache_key)
        if twentyfour is None and cache_key not in twentyfour_cache:
            if create_missing:
                if dry_run:
                    twentyfour_cache[cache_key] = None
                    skipped_missing_parent += 1
                    continue
                twentyfour, _ = MarketTrading24Hour.objects.get_or_create(
                    session_group=sg,
                    symbol=symbol,
                    defaults={
                        "session_date": row.timestamp_minute.date(),
                        "country": country,
                    },
                )
                twentyfour_cache[cache_key] = twentyfour
            else:
                twentyfour_cache[cache_key] = None
                skipped_missing_parent += 1
                continue

        if twentyfour is None:
            continue

        row.twentyfour = twentyfour
        buffer.append(row)

        if len(buffer) >= batch_size:
            flush_buffer(buffer)
            linked += len(buffer)
            buffer.clear()

    if buffer:
        flush_buffer(buffer)
        linked += len(buffer)

    if dry_run:
        stdout.write(
            style.WARNING(
                f"Dry-run: processed={processed} linkable={linked} skipped_missing_parent={skipped_missing_parent}"
            )
        )
        return

    if verbose:
        stdout.write(
            f"Processed={processed} linked={linked} skipped_missing_parent={skipped_missing_parent}"
        )

    stdout.write(
        style.SUCCESS(
            f"Processed={processed} linked={linked} skipped_missing_parent={skipped_missing_parent} pending={max(processed - linked, 0)}"
        )
    )
