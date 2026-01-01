from __future__ import annotations

"""Futures Total management command entrypoints.

These modules define the actual Django `Command` classes, but Django will still
*discover* commands from `ThorTrading.management.commands`.

The discoverable modules in `ThorTrading.management.commands` should remain as
ultra-thin shims that import `Command` from here.

Business logic continues to live under `ThorTrading.studies.futures_total.command_logic`.
"""

__all__: list[str] = []
