"""
Data Provider Implementations for SchwabLiveData

PURPOSE:
    Implements the core data provider classes that fetch and normalize market data
    from different sources. This file contains the actual provider implementations,
    while provider_factory.py handles provider selection and configuration.

RESPONSIBILITIES:
    - Defines the BaseProvider interface all providers must implement
    - Provides concrete implementations of data providers (ExcelLive via import)
    - Normalizes raw data into a consistent API format
    - Manages provider-specific business logic

KEY COMPONENTS:
    - BaseProvider: Abstract base class defining the provider interface
    - SchwabProvider: Placeholder for future Schwab API integration
    - create_provider(): Factory function for creating provider instances
    - Data normalization utilities for converting Excel/API data to standard format

USAGE:
    # Create a provider directly (normally done via provider_factory.py)
    provider = create_provider('excel_live', 
                              excel_file='path/to/file.xlsm',
                              sheet_name='Futures')
    
    # Get data from a provider
    quotes = provider.get_latest_quotes(['/YM', '/ES', '/NQ'])
    
    # Check provider health
    health = provider.health_check()
"""

import os
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import threading

# Import Excel Live provider from dedicated module
try:
    from .excel_live import ExcelLiveProvider  # type: ignore
except Exception:
    ExcelLiveProvider = None  # Optional dependency; factory will raise if requested


class BaseProvider(ABC):
    """Abstract base class for all market data providers."""
    
    @abstractmethod
    def get_latest_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Return latest market data for the given symbols.
        
        Args:
            symbols: List of instrument symbols (e.g., ['/YM', '/ES', '/NQ'])
            
        Returns:
            List of market data dictionaries matching the API schema
        """
        raise NotImplementedError()
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Return provider health status and metadata.
        
        Returns:
            Dictionary with provider status, connection info, rate limits, etc.
        """
        raise NotImplementedError()
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this provider."""
        raise NotImplementedError()


class SchwabProvider(BaseProvider):
    """
    Placeholder provider for Schwab API integration.
    
    This will be implemented when Schwab API credentials are available.
    For now, it raises NotImplementedError to clearly indicate it's not ready.
    """
    
    def __init__(self, config: Dict[str, Any]):
        from .schwab_client import SchwabApiClient  # Lazy import to keep dependency surface small
        self.config = config or {}
        self.client = SchwabApiClient(self.config)
        self._connected = False
        # Note: actual OAuth handshake will be performed when permissions are granted
    
    def get_latest_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch real market data from Schwab API.
        
        TODO: Implement when Schwab API access is available:
        1. Authenticate with OAuth2
        2. Make REST API calls to Schwab
        3. Map Schwab response fields to our standard schema
        4. Handle rate limits and errors
        """
        # The implementation will:
        # - Ensure valid access token (refresh if needed)
        # - Call quotes endpoint and transform response to our schema
        # For now, we raise 501 to signal upstream that the provider exists but is not yet enabled.
        raise NotImplementedError("Schwab API integration pending approval; provider scaffolded but not active.")
    
    def health_check(self) -> Dict[str, Any]:
        """Return health status for Schwab provider."""
        info = self.client.health()
        return {
            "provider": "schwab",
            "connected": bool(info.get("configured")) and bool(self._connected),
            "status": info.get("status", "not_configured"),
            "auth": info.get("auth", {}),
            "oauth": info.get("oauth", {}),
            # Report effective values from the client (env/.env resolved)
            "base_url": getattr(self.client, "base_url", None),
            "scopes": getattr(self.client, "scopes", None),
        }
    
    def get_provider_name(self) -> str:
        return "Schwab API Provider (Not Implemented)"


def create_provider(provider_type: str, **kwargs) -> BaseProvider:
    """
    Factory function to create the appropriate provider.
    
    Args:
        provider_type: 'excel_live' or 'schwab'
        **kwargs: Provider-specific configuration
        
    Returns:
        Configured provider instance
        
    Raises:
        ValueError: If provider_type is not supported
    """
    # Remove the 'excel' option from here
    if provider_type.lower() == 'excel_live':
        if ExcelLiveProvider is None:
            raise RuntimeError("Excel Live provider requested but xlwings is not installed.")
        excel_file = kwargs.get('excel_file')
        sheet_name = kwargs.get('sheet_name', 'Futures')
        live_range = kwargs.get('live_range', 'A1:M16')
        poll_ms = int(kwargs.get('poll_ms', 150))
        require_open = bool(kwargs.get('require_open', False))
        prov = ExcelLiveProvider(
            file_path=excel_file,
            sheet_name=sheet_name,
            range_address=live_range,
            poll_ms=poll_ms,
            require_open=require_open,
        )
        # Start polling thread immediately
        if hasattr(prov, 'start'):
            prov.start()
        return prov
    
    elif provider_type.lower() == 'schwab':
        config = kwargs.get('config', {})
        return SchwabProvider(config)
    
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")