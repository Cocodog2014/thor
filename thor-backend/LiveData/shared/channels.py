"""
Redis channel naming conventions for LiveData feeds.

Centralizes channel names to prevent typos and ensure consistency
across all broker integrations.
"""

# Quote channels (real-time market data)
QUOTES_CHANNEL = "live_data:quotes:{symbol}"

# Position channels (holdings per account)
POSITIONS_CHANNEL = "live_data:positions:{account_id}"

# Balance channels (cash/buying power)
BALANCES_CHANNEL = "live_data:balances:{account_id}"

# Order channels (order fills/updates)
ORDERS_CHANNEL = "live_data:orders:{account_id}"

# Transaction channels (buy/sell history)
TRANSACTIONS_CHANNEL = "live_data:transactions:{account_id}"


def get_quotes_channel(symbol: str) -> str:
    """Get the Redis channel for a specific symbol's quotes."""
    return QUOTES_CHANNEL.format(symbol=symbol.upper())


def get_positions_channel(account_id: str) -> str:
    """Get the Redis channel for an account's positions."""
    return POSITIONS_CHANNEL.format(account_id=account_id)


def get_balances_channel(account_id: str) -> str:
    """Get the Redis channel for an account's balances."""
    return BALANCES_CHANNEL.format(account_id=account_id)


def get_orders_channel(account_id: str) -> str:
    """Get the Redis channel for an account's orders."""
    return ORDERS_CHANNEL.format(account_id=account_id)


def get_transactions_channel(account_id: str) -> str:
    """Get the Redis channel for an account's transactions."""
    return TRANSACTIONS_CHANNEL.format(account_id=account_id)
