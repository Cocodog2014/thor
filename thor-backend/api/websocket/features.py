"""
WebSocket Feature Flags - Phased Cutover

Controls which features use WebSocket vs REST endpoints.
One feature at a time: verify WS works, then mark REST timer for deletion.

APP ORGANIZATION:
- account_balance, positions → ActAndPos app (user account/position data)
- intraday, vwap → ThorTrading app (trading data, bars)
- global_market → GlobalMarkets app (market indices, Japan/China markets, holidays)

Cutover order:
1. account_balance - Account balance (ActAndPos)
2. positions - Position data (ActAndPos)
3. intraday - Intraday bar data (ThorTrading)
4. global_market - Global market status (GlobalMarkets - US/Japan/China markets)
"""

import os


class WebSocketFeatureFlags:
    """Feature flags for WebSocket cutover."""
    
    # Feature cutover status: True = use WebSocket, False = use REST (shadow mode)
    ACCOUNT_BALANCE_WS = os.getenv("WS_FEATURE_ACCOUNT_BALANCE", "false").lower() == "true"
    POSITIONS_WS = os.getenv("WS_FEATURE_POSITIONS", "false").lower() == "true"
    INTRADAY_WS = os.getenv("WS_FEATURE_INTRADAY", "false").lower() == "true"
    GLOBAL_MARKET_WS = os.getenv("WS_FEATURE_GLOBAL_MARKET", "false").lower() == "true"
    
    @classmethod
    def get_status(cls) -> dict[str, bool]:
        """Return feature cutover status."""
        return {
            "account_balance": cls.ACCOUNT_BALANCE_WS,
            "positions": cls.POSITIONS_WS,
            "intraday": cls.INTRADAY_WS,
            "global_market": cls.GLOBAL_MARKET_WS,
        }
    
    @classmethod
    def all_live(cls) -> bool:
        """True if all features are using WebSocket."""
        return all(cls.get_status().values())
    
    @classmethod
    def any_live(cls) -> bool:
        """True if any feature is using WebSocket."""
        return any(cls.get_status().values())
