"""Compatibility shim for the closed bars flush job.

The job now lives in ThorTrading.realtime.jobs.closed_bars_flush. Prefer importing
from that module; this shim will be removed after callers migrate.
"""

from ThorTrading.realtime.jobs.closed_bars_flush import ClosedBarsFlushJob  # noqa: F401
