"""Compatibility shim for VWAP minute job location change.

Use ThorTrading.realtime.jobs.vwap_minute_capture instead of this module.
"""

from ThorTrading.realtime.jobs.vwap_minute_capture import VwapMinuteCaptureJob  # noqa: F401
