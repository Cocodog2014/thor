"""
WebSocket Message Builders

All message formats defined here (presentation layer).
Domain apps build their data, this module formats it for WebSocket clients.
"""

from typing import Any, Dict


# Account & Position Messages (from ActAndPos app)

def build_account_balance_message(balance_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build account balance message for WebSocket.
    
    Args:
        balance_data: Dictionary with cash, portfolio_value, buying_power, timestamp, etc.
    
    Returns:
        Message dict with type='account_balance'
    """
    return {
        "type": "account_balance",
        "data": balance_data,
    }


def build_positions_message(positions_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build positions message for WebSocket.
    
    Args:
        positions_data: Dictionary with positions list and metadata
    
    Returns:
        Message dict with type='positions'
    """
    return {
        "type": "positions",
        "data": positions_data,
    }


# Trading Data Messages (from ThorTrading app)

def build_intraday_bar_message(bar_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build intraday bar message for WebSocket.
    
    Args:
        bar_data: Dictionary with symbol, timestamp, OHLCV data
    
    Returns:
        Message dict with type='intraday_bar'
    """
    return {
        "type": "intraday_bar",
        "data": bar_data,
    }


def build_vwap_message(vwap_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build VWAP message for WebSocket.
    
    Args:
        vwap_data: Dictionary with symbol, vwap value, volume, timestamp
    
    Returns:
        Message dict with type='vwap_update'
    """
    return {
        "type": "vwap_update",
        "data": vwap_data,
    }


# Global Market Messages (from GlobalMarkets app)

def build_market_status_message(status_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build global market status message for WebSocket.
    
    For global market data like:
    - US market open/close status
    - Japan market status
    - China market status
    - Market sessions (pre-market, regular, after-hours)
    - Market holidays
    - Market indices (S&P 500, NASDAQ, DOW)
    
    Args:
        status_data: Dictionary with market open/close status, session info, indices
    
    Returns:
        Message dict with type='market_status'
    """
    return {
        "type": "market_status",
        "data": status_data,
    }
