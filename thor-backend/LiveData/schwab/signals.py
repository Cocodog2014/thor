"""Deprecated shim.

Subscription rows are now owned by the Instruments app (product state). This module is kept
only to avoid breaking any accidental imports of `LiveData.schwab.signals`.
"""

from Instruments import schwab_subscription_signals as _signals  # noqa: F401
