# ThorTrading/services/sessions/global_market_gate.py

def market_enabled(market) -> bool:
    """
    Master switch: is this market enabled at all?
    """
    return bool(getattr(market, "is_active", False))


def session_tracking_allowed(market) -> bool:
    """
    Can ThorTrading run intraday/session workers and write MarketSession rows?
    """
    return (
        market_enabled(market)
        and bool(getattr(market, "enable_session_capture", True))
    )


def open_capture_allowed(market) -> bool:
    """
    Can ThorTrading capture market OPEN events?
    """
    return (
        market_enabled(market)
        and bool(getattr(market, "enable_open_capture", True))
    )


def close_capture_allowed(market) -> bool:
    """
    Can ThorTrading capture market CLOSE events?
    """
    return (
        market_enabled(market)
        and bool(getattr(market, "enable_close_capture", True))
    )
