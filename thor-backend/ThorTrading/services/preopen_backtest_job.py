"""Compatibility shim for pre-open backtest job location change.

Use ThorTrading.realtime.jobs.preopen_backtest instead of this module.
"""

from ThorTrading.realtime.jobs.preopen_backtest import PreOpenBacktestJob  # noqa: F401
