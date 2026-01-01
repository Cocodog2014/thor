from __future__ import annotations


def run(*, stdout, style) -> None:
    stdout.write(
        style.WARNING(
            "Nothing to do: MarketSession.capture_group was removed; session_number is the grouping key."
        )
    )
