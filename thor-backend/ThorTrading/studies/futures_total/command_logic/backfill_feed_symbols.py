from __future__ import annotations


def run(*, dry_run: bool, batch_size: int, verbose: bool, stdout, style) -> None:
    stdout.write(
        style.WARNING(
            "TradingInstrument/feed_symbol has been retired in the full migration. "
            "This command is now a no-op."
        )
    )
