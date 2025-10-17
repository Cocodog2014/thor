"""
LiveData - Multi-broker live market data pipeline

This package provides a unified interface for fetching and streaming
live market data from multiple brokers (Schwab, TOS, IBKR, etc.).

Structure:
- shared/: Redis client and shared utilities
- schwab/: Schwab OAuth + Trading API integration
- tos/: Thinkorswim real-time streaming
"""

__version__ = "1.0.0"
