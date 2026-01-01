"""
Import study modules so they self-register.
Keep it explicit (no magic autodiscovery) so it stays predictable.
"""
from ThorTrading.studies.futures_total import study as _futures_total  # noqa: F401
