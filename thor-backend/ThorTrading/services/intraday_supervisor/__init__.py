from __future__ import annotations

"""Compatibility package (safe imports).

This package intentionally does not import intraday supervisors at import-time.
Some older modules import utility helpers from this namespace; those should be
migrated to `ThorTrading.intraday.*`.
"""

__all__: list[str] = []
