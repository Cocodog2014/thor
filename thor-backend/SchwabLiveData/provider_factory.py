"""
Provider Factory for SchwabLiveData

PURPOSE:
    Manages creation and configuration of market data providers,
    with Excel Live as the primary provider for real-time market data.

RESPONSIBILITIES:
    - Creates and configures the ExcelLiveProvider
    - Manages provider lifecycle and caching
    - Resolves configuration from environment variables
    - Ensures a single provider instance is reused across requests
    - Provides status and health information for diagnostics

KEY COMPONENTS:
    - ProviderConfig: Configuration class for provider settings
    - get_market_data_provider(): Factory function to get/create providers
    - Provider caching to maintain a single instance with polling thread
    - Excel file path resolution with fallback options

CONFIGURATION (Environment Variables):
    - DATA_PROVIDER: Always "excel_live" in this implementation
    - EXCEL_DATA_FILE: Path to Excel workbook with market data
    - EXCEL_SHEET_NAME: Name of sheet containing futures data
    - EXCEL_LIVE_RANGE: Cell range to poll (e.g., "A1:M20")
    - EXCEL_LIVE_REQUIRE_OPEN: Whether workbook must be open (0/1)
    - EXCEL_LIVE_POLL_MS: Polling frequency in milliseconds

USAGE:
    # Get a provider using environment configuration
    provider = get_market_data_provider()
    
    # Get latest quotes for default symbols
    quotes = provider.get_latest_quotes(ProviderConfig.DEFAULT_SYMBOLS)
    
    # Check provider health/status
    status = get_provider_status()
"""

import os
from typing import Optional
from django.conf import settings
from .providers import BaseProvider, SchwabProvider, create_provider
from .excel_live import ExcelLiveProvider

# --- Simple in-process provider cache ---
# We must reuse the same provider instance across requests
_CACHED_PROVIDER: BaseProvider | None = None
_CACHED_CONFIG: dict | None = None


class ProviderConfig:
    """Configuration class for provider settings."""
    
    # Default futures symbols (11 futures as shown in dashboard)
    DEFAULT_SYMBOLS = [
        "/YM", "/ES", "/NQ", "RTY",  # Equity index futures
        "CL", "SI", "HG", "GC",      # Commodities  
        "VX", "DX", "ZB"             # Vol, Dollar, Bonds
    ]
    
    def __init__(self, request=None):
        # Provider type is now fixed to excel_live
        self.provider = "excel_live"
        
        # Excel file configuration
        self.excel_file = (request.GET.get("excel_file") if request else None) or os.getenv("EXCEL_DATA_FILE")
        self.excel_sheet = (request.GET.get("sheet_name") if request else None) or os.getenv("EXCEL_SHEET_NAME") or "Futures"
        self.excel_range = (request.GET.get("range") if request else None) or os.getenv("EXCEL_LIVE_RANGE") or "A1:M20"
        
        # Excel Live specific settings
        excel_live_require = (request.GET.get("require_open") if request else None) or os.getenv("EXCEL_LIVE_REQUIRE_OPEN") or "0"
        self.require_open = str(excel_live_require).lower() in ("1", "true", "yes", "on")
        
        # Poll frequency in milliseconds
        self.poll_ms = int((request.GET.get("poll_ms") if request else None) or os.getenv("EXCEL_LIVE_POLL_MS") or "200")

    @staticmethod
    def get_excel_file_path() -> str:
        """Resolve Excel file path.

        Precedence:
        1) EXCEL_DATA_FILE env or Django setting (absolute or relative to app dir)
        2) First existing among: Futures.xlsm, Futures.xlsx, CleanData.xlsm, CleanData.xlsx
        """
        app_dir = os.path.dirname(__file__)
        configured = os.getenv("EXCEL_DATA_FILE") or getattr(settings, "EXCEL_DATA_FILE", None)
        if configured:
            if os.path.isabs(configured):
                return configured
            return os.path.join(app_dir, configured)

        candidates = [
            "Futures.xlsm", "Futures.xlsx", "CleanData.xlsm", "CleanData.xlsx"
        ]
        for name in candidates:
            p = os.path.join(app_dir, name)
            if os.path.exists(p):
                return p
        # Fall back to Futures.xlsm path even if missing (will error later)
        return os.path.join(app_dir, "Futures.xlsm")


def clear_provider_cache() -> None:
    """Clear the cached provider (useful for tests or config changes)."""
    global _CACHED_PROVIDER, _CACHED_CONFIG
    _CACHED_PROVIDER = None
    _CACHED_CONFIG = None


def _config_snapshot(config: ProviderConfig) -> tuple:
    """Create a snapshot of the configuration for cache comparison."""
    return (
        config.provider,
        config.excel_file,
        config.excel_sheet,
        config.excel_range,
        config.require_open,
        config.poll_ms,
    )


def get_market_data_provider(config: ProviderConfig = None):
    """Return an Excel Live provider instance.
    
    This function initializes an ExcelLiveProvider based on the given configuration.
    If no config is provided, it creates one using environment variables and settings.
    The provider instance is cached to ensure the polling thread persists across requests.
    
    Args:
        config: Optional ProviderConfig instance
        
    Returns:
        ExcelLiveProvider instance
        
    Raises:
        Exception: If the provider cannot be initialized
    """
    global _CACHED_PROVIDER, _CACHED_CONFIG
    
    # Create default config if none provided
    if config is None:
        config = ProviderConfig()
    
    # Check if we can reuse the cached provider
    snap = _config_snapshot(config)
    if _CACHED_PROVIDER is not None and _CACHED_CONFIG == snap:
        return _CACHED_PROVIDER

    # Get Excel file path
    excel_file = config.excel_file or ProviderConfig.get_excel_file_path()
    sheet = config.excel_sheet or "Futures"
    
    # Initialize Excel Live provider
    try:
        provider = ExcelLiveProvider(
            file_path=excel_file,
            sheet_name=sheet,
            range_address=config.excel_range or "A1:M20",
            poll_ms=config.poll_ms,
            require_open=config.require_open,
        )
        provider.start()
        
        # Cache the provider
        _CACHED_PROVIDER = provider
        _CACHED_CONFIG = snap
        return provider
    except Exception as e:
        # Log error and raise - no fallbacks
        print(f"Excel Live initialization failed: {e}")
        raise


def get_provider_status() -> dict:
    """
    Get the current provider configuration and status.
    
    Returns:
        Dictionary with provider info, configuration, and health status
    """
    try:
        cfg = ProviderConfig()
        provider = get_market_data_provider(cfg)
        health = provider.health_check() if hasattr(provider, 'health_check') else None
        
        return {
            "provider_type": "excel_live",
            "provider_name": provider.get_provider_name() if hasattr(provider, 'get_provider_name') else "ExcelLiveProvider",
            "symbols_count": len(ProviderConfig.DEFAULT_SYMBOLS),
            "excel_file": cfg.excel_file or ProviderConfig.get_excel_file_path(),
            "excel_sheet": cfg.excel_sheet,
            "excel_range": cfg.excel_range,
            "poll_ms": cfg.poll_ms,
            "require_open": cfg.require_open,
            "health": health,
            "status": "ok"
        }
    except Exception as e:
        return {
            "provider_type": "excel_live",
            "error": str(e),
            "status": "error"
        }