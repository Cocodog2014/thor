from __future__ import annotations

"""Canonical Schwab streaming field lists.

These lists define which quote attributes we request from Schwab streaming.
They live in Instruments so the domain that owns "what a quote contains" owns
these knobs (bid/ask/last/volume/timestamps, etc.).

`schwab_stream.py` maps these names onto schwab-py StreamClient field enums.
"""

SCHWAB_LEVEL_ONE_EQUITY_FIELDS: tuple[str, ...] = (
    "SYMBOL",
    "BID_PRICE",
    "ASK_PRICE",
    "LAST_PRICE",
    # Some symbols (notably indexes) may not populate LAST_PRICE reliably; MARK is
    # often the most useful real-time value.
    "MARK",
    "TOTAL_VOLUME",
    "QUOTE_TIME_MILLIS",
    "TRADE_TIME_MILLIS",
)


# Futures field names are filtered by schwab_stream at runtime via
# `hasattr(StreamClient.LevelOneFuturesFields, name)` to avoid breakage if
# schwab-py changes its enum surface.
SCHWAB_LEVEL_ONE_FUTURES_FIELDS: tuple[str, ...] = (
    "SYMBOL",
    "BID_PRICE",
    "ASK_PRICE",
    "LAST_PRICE",
    # Include MARK when available (guarded by hasattr() in schwab_stream).
    "MARK",
    "TOTAL_VOLUME",
    "QUOTE_TIME_MILLIS",
    "TRADE_TIME_MILLIS",
)

