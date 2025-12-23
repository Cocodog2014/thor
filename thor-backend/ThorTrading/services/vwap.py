"""Compatibility shim for the VWAP service moved to services.indicators.vwap."""

from ThorTrading.services.indicators.vwap import VwapResult, VwapService, vwap_service

__all__ = ["vwap_service", "VwapService", "VwapResult"]

