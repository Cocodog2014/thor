from __future__ import annotations

from ThorTrading.studies.futures_total.models.rtd import TradingInstrument


def run(*, dry_run: bool, batch_size: int, verbose: bool, stdout, style) -> None:
    updated_feed = 0
    updated_symbol = 0
    processed = 0

    qs = TradingInstrument.objects.all().order_by("pk")
    start = 0
    while True:
        batch = list(qs[start : start + batch_size])
        if not batch:
            break
        start += batch_size

        for inst in batch:
            processed += 1
            feed = inst.feed_symbol.strip() if inst.feed_symbol else ""
            if feed:
                continue

            symbol = inst.symbol or ""
            if not symbol.startswith("/"):
                continue

            candidate_feed = symbol
            candidate_symbol = symbol.lstrip("/") or symbol

            can_update_symbol = False
            if candidate_symbol != symbol:
                exists = (
                    TradingInstrument.objects.filter(symbol=candidate_symbol)
                    .exclude(pk=inst.pk)
                    .exists()
                )
                can_update_symbol = not exists

            if not dry_run:
                inst.feed_symbol = candidate_feed
                fields = ["feed_symbol"]
                if can_update_symbol:
                    inst.symbol = candidate_symbol
                    fields.append("symbol")
                    updated_symbol += 1
                inst.save(update_fields=fields)
            else:
                if can_update_symbol:
                    updated_symbol += 1

            updated_feed += 1

        if verbose:
            stdout.write(
                f"Processed={processed} updated_feed={updated_feed} updated_symbol={updated_symbol}"
            )

    if dry_run:
        stdout.write(
            style.WARNING(
                f"Dry-run: feed_symbol to set={updated_feed}, symbols to normalize={updated_symbol}"
            )
        )
        return

    stdout.write(
        style.SUCCESS(
            f"Updated feed_symbol on {updated_feed} instruments; normalized symbol on {updated_symbol} (where no conflicts)."
        )
    )
