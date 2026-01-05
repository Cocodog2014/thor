from __future__ import annotations

import threading
from contextlib import contextmanager


_local = threading.local()


def signals_suppressed() -> bool:
    return bool(getattr(_local, "suppress_schwab_subscription_signals", False))


@contextmanager
def suppress_schwab_subscription_signals():
    prev = getattr(_local, "suppress_schwab_subscription_signals", False)
    _local.suppress_schwab_subscription_signals = True
    try:
        yield
    finally:
        _local.suppress_schwab_subscription_signals = prev
