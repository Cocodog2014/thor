"""Stub VWAP service (no-op).

Provides vwap_service with get_current_vwap(symbol) returning None.
Used only to satisfy existing imports until full VWAP integration needed.
"""
from __future__ import annotations

class _StubVwapService:
    def get_current_vwap(self, symbol: str):
        return None

vwap_service = _StubVwapService()

__all__ = ["vwap_service"]
