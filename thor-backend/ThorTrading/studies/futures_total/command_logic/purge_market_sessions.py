from __future__ import annotations

from ThorTrading.models.MarketSession import MarketSession


def run(*, dry_run: bool, yes_i_am_sure: bool, confirm: str | None, stdout, style) -> None:
    count = MarketSession.objects.count()
    if dry_run:
        stdout.write(style.WARNING(f"Dry run: would purge {count} MarketSession rows."))
        return

    if not yes_i_am_sure:
        raise ValueError("Refusing to purge without --yes-i-am-sure")

    if confirm != "DELETE":
        raise ValueError("Refusing to purge without --confirm DELETE")

    MarketSession.objects.all().delete()
    stdout.write(style.SUCCESS(f"Purged {count} MarketSession rows."))
