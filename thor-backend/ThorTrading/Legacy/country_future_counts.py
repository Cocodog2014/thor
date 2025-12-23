"""Compatibility shim for CountryFutureCounter location change.

Use ThorTrading.services.sessions.counters instead of this module.
"""

from ThorTrading.services.sessions.counters import CountryFutureCounter  # noqa: F401

__all__ = ["CountryFutureCounter"]
