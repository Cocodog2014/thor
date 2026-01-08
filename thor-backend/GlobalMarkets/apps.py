def ready(self):
    import os
    import logging
    logger = logging.getLogger(__name__)

    if os.environ.get("GLOBAL_MARKETS_READY") == "1":
        return
    os.environ["GLOBAL_MARKETS_READY"] = "1"

    # Signals only (keep GlobalMarkets decoupled)
    import GlobalMarkets.signals  # noqa: F401
