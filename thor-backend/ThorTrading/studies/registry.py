from __future__ import annotations

from typing import Any, Dict

# Minimal in-process registry for study modules that self-register on import.
# This is intentionally lightweight: ThorTrading's realtime scheduler uses
# ThorTrading.studies.realtime_provider.register (different concern).

_STUDIES: Dict[str, Any] = {}


def register(study: Any) -> None:
    """Register a study instance by its stable key."""
    key = getattr(study, "key", None) or getattr(study, "code", None) or study.__class__.__name__
    _STUDIES[str(key)] = study


def get(key: str) -> Any | None:
    return _STUDIES.get(str(key))


def all() -> Dict[str, Any]:
    return dict(_STUDIES)
