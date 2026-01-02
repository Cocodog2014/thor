from __future__ import annotations

"""Legacy services namespace.

Canonical services live in `ThorTrading.studies.futures_total.services`.

This package keeps `ThorTrading.services.*` imports working by extending
its module search path to include the canonical services directory.
"""

from pathlib import Path


# Ensure imports like `ThorTrading.services.indicators...` resolve from the
# study-owned services directory without needing per-module shims.
_here = Path(__file__).resolve().parent
_canonical = _here.parent / "studies" / "futures_total" / "services"

if _canonical.exists():
	__path__.append(str(_canonical))
