"""
Provider Factory for SchwabLiveData

This module handles the selection and configuration of market data providers.
It allows switching between JSON (fake data) and Schwab API providers via
environment variables or database configuration.
"""

import os
from typing import Optional
from django.conf import settings
from .providers import BaseProvider, JSONProvider, SchwabProvider, create_provider
from .excel_live import ExcelLiveProvider  # NEW

# --- Simple in-process provider cache ---
# We must reuse the same provider instance across requests so that
# JSONProvider's random generator and iteration counter advance over time.
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
    
    # Provider type preferences (in order of preference)
    PROVIDER_PRIORITY = ["schwab", "excel_live", "excel", "json"]
    
    def __init__(self, request=None):
        # Request-specific overrides (for testing or dynamic config)
        self.provider = (request.GET.get("provider") if request else None) or os.getenv("DATA_PROVIDER") or "excel"
        self.excel_file = (request.GET.get("excel_file") if request else None) or os.getenv("EXCEL_DATA_FILE")
        self.excel_sheet = (request.GET.get("sheet_name") if request else None) or os.getenv("EXCEL_SHEET_NAME") or "Futures"
        self.excel_range = (request.GET.get("range") if request else None) or os.getenv("EXCEL_RANGE") or "A1:M20"
        
        # Auto-enable Excel Live when provider is 'excel_live', or check explicit EXCEL_LIVE setting
        if self.provider == "excel_live":
            self.excel_live = True
        else:
            excel_live_env = (request.GET.get("excel_live") if request else None) or os.getenv("EXCEL_LIVE") or "0"
            self.excel_live = str(excel_live_env).lower() in ("1", "true", "yes", "on")
            
        self.live_sim = (request.GET.get("live_sim") if request else None) or os.getenv("ENABLE_LIVE_SIMULATION") or "false"
        self.live_sim = str(self.live_sim).lower() in ("1", "true", "yes", "on")

    @staticmethod
    def get_json_file_path() -> str:
        """Get the path to the JSON data file."""
        # Look for explicit JSON file override first
        app_dir = os.path.dirname(__file__)
        explicit = os.getenv("JSON_DATA_FILE")
        if explicit:
            # If an absolute path is provided, use it directly; otherwise resolve in app dir
            if os.path.isabs(explicit):
                return explicit
            return os.path.join(app_dir, explicit)

        # Default
        return os.path.join(app_dir, "futures_data.json")

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

    @staticmethod
    def get_excel_live_settings() -> dict:
        """Return Excel Live specific settings from env/settings with sane defaults."""
        from django.conf import settings as dj
        return {
            "excel_range": os.getenv("EXCEL_LIVE_RANGE", getattr(dj, "EXCEL_LIVE_RANGE", "A1:M16")),
            "poll_ms": int(os.getenv("EXCEL_LIVE_POLL_MS", getattr(dj, "EXCEL_LIVE_POLL_MS", 150))),
            "require_open": os.getenv("EXCEL_LIVE_REQUIRE_OPEN", str(getattr(dj, "EXCEL_LIVE_REQUIRE_OPEN", "false"))).lower() in ["1","true","yes","on"],
        }
    
    @staticmethod
    def get_provider_type() -> str:
        """
        Determine which provider to use based on configuration.
        
        Priority order:
        1. Environment variable DATA_PROVIDER
        2. Django setting DATA_PROVIDER  
        3. Database DataProviderConfig (if implemented)
        4. Default to 'json'
        """
        # Check environment variable first
        env_provider = os.getenv("DATA_PROVIDER", "").lower()
        if env_provider in ["json", "schwab", "excel", "excel_live"]:
            return env_provider
            
        # Check Django settings
        settings_provider = getattr(settings, "DATA_PROVIDER", "").lower()
        if settings_provider in ["json", "schwab", "excel", "excel_live"]:
            return settings_provider
            
        # TODO: Check database DataProviderConfig if implemented
        # db_provider = get_db_provider_config()
        # if db_provider:
        #     return db_provider
            
        # Default to JSON provider
        return "json"
    
    @staticmethod
    def get_live_simulation_enabled() -> bool:
        """Check if live price simulation should be enabled."""
        # Environment variable takes precedence
        env_value = os.getenv("ENABLE_LIVE_SIMULATION", "").lower()
        if env_value in ["true", "1", "yes", "on"]:
            return True
        elif env_value in ["false", "0", "no", "off"]:
            return False
            
        # Django setting
        return getattr(settings, "ENABLE_LIVE_SIMULATION", True)


def _provider_config_snapshot(provider_type: str, json_file: str | None, live_sim: bool, symbols: list[str]) -> dict:
    """Create a comparable config snapshot used to validate the cache."""
    return {
        "provider_type": provider_type,
        "json_file": json_file,
        "live_sim": live_sim,
        # Symbols can influence provider behavior (sort_order), include for safety
        "symbols": tuple(symbols),
    }


def clear_provider_cache() -> None:
    """Clear the cached provider (useful for tests or config changes)."""
    global _CACHED_PROVIDER, _CACHED_CONFIG
    _CACHED_PROVIDER = None
    _CACHED_CONFIG = None


def get_market_data_provider(symbols: Optional[list] = None, disable_fallback: bool = False) -> BaseProvider:
    """
    Factory function to get the configured market data provider.
    
    Args:
        symbols: List of symbols to fetch (uses default if None)
        
    Returns:
        Configured provider instance
        
    Raises:
        ValueError: If provider configuration is invalid
        RuntimeError: If provider initialization fails
    """
    global _CACHED_PROVIDER, _CACHED_CONFIG

    if symbols is None:
        symbols = ProviderConfig.DEFAULT_SYMBOLS
    
    provider_type = ProviderConfig.get_provider_type()
    
    try:
        if provider_type == "json":
            json_file = ProviderConfig.get_json_file_path()
            live_sim = ProviderConfig.get_live_simulation_enabled()

            # Verify JSON file exists
            if not os.path.exists(json_file):
                raise FileNotFoundError(f"JSON data file not found: {json_file}")

            # Attempt to reuse cached provider if config matches
            config_now = _provider_config_snapshot(provider_type, json_file, live_sim, symbols)
            if _CACHED_PROVIDER is not None and _CACHED_CONFIG == config_now:
                return _CACHED_PROVIDER

            # Create and cache a new provider
            provider = create_provider("json", json_file=json_file, live_simulation=live_sim)
            _CACHED_PROVIDER = provider
            _CACHED_CONFIG = config_now
            return provider
            
        elif provider_type == "excel":
            excel_file = ProviderConfig.get_excel_file_path()
            sheet_name = os.getenv("EXCEL_SHEET_NAME", getattr(settings, "EXCEL_SHEET_NAME", "Futures"))
            live_sim = ProviderConfig.get_live_simulation_enabled()

            # Verify Excel file exists (helpful error if not)
            if not os.path.exists(excel_file):
                raise FileNotFoundError(f"Excel data file not found: {excel_file}")

            # Cache config
            config_now = {
                "provider_type": provider_type,
                "excel_file": excel_file,
                "sheet": sheet_name,
                "live_sim": live_sim,
                "symbols": tuple(symbols),
            }
            if _CACHED_PROVIDER is not None and _CACHED_CONFIG == config_now:
                return _CACHED_PROVIDER

            provider = create_provider("excel", excel_file=excel_file, sheet_name=sheet_name, live_simulation=live_sim)
            _CACHED_PROVIDER = provider
            _CACHED_CONFIG = config_now
            return provider

        elif provider_type == "excel_live":
            excel_file = ProviderConfig.get_excel_file_path()
            sheet_name = os.getenv("EXCEL_SHEET_NAME", getattr(settings, "EXCEL_SHEET_NAME", "Futures"))
            live = ProviderConfig.get_excel_live_settings()

            if not os.path.exists(excel_file):
                raise FileNotFoundError(f"Excel data file not found: {excel_file}")

            config_now = {
                "provider_type": provider_type,
                "excel_file": excel_file,
                "sheet": sheet_name,
                "excel_range": live["excel_range"],
                "poll_ms": live["poll_ms"],
                "require_open": live["require_open"],
                "symbols": tuple(symbols),
            }
            if _CACHED_PROVIDER is not None and _CACHED_CONFIG == config_now:
                return _CACHED_PROVIDER

            provider = create_provider(
                "excel_live",
                excel_file=excel_file,
                sheet_name=sheet_name,
                live_range=live["excel_range"],
                poll_ms=live["poll_ms"],
                require_open=live["require_open"],
            )
            _CACHED_PROVIDER = provider
            _CACHED_CONFIG = config_now
            return provider

        elif provider_type == "schwab":
            # TODO: Load Schwab configuration from environment/settings
            schwab_config = {
                "client_id": os.getenv("SCHWAB_CLIENT_ID"),
                "client_secret": os.getenv("SCHWAB_CLIENT_SECRET"), 
                "base_url": os.getenv("SCHWAB_BASE_URL", "https://api.schwabapi.com"),
                "scopes": os.getenv("SCHWAB_SCOPES", "read").split(",")
            }
            
            # Validate required Schwab config
            if not schwab_config["client_id"] or not schwab_config["client_secret"]:
                raise ValueError(
                    "Schwab provider requires SCHWAB_CLIENT_ID and SCHWAB_CLIENT_SECRET "
                    "environment variables. Set DATA_PROVIDER=json to use mock data."
                )
                
            # For Schwab provider, also cache instance so connections/tokens can persist
            config_now = {
                "provider_type": provider_type,
                "config": tuple(sorted((schwab_config or {}).items())),
                "symbols": tuple(symbols),
            }
            if _CACHED_PROVIDER is not None and _CACHED_CONFIG == config_now:
                return _CACHED_PROVIDER

            provider = create_provider("schwab", config=schwab_config)
            _CACHED_PROVIDER = provider
            _CACHED_CONFIG = config_now
            return provider
            
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
            
    except Exception as e:
        # Log the error and fall back to JSON provider if possible
        print(f"Provider initialization failed for {provider_type}: {e}")
        
        if provider_type != "json" and not disable_fallback:
            print("Falling back to JSON provider...")
            try:
                json_file = ProviderConfig.get_json_file_path()
                provider = create_provider("json", json_file=json_file, live_simulation=True)
                # Update cache on fallback as well
                _CACHED_PROVIDER = provider
                _CACHED_CONFIG = _provider_config_snapshot("json", json_file, True, symbols)
                return provider
            except Exception as fallback_error:
                raise RuntimeError(f"Provider fallback failed: {fallback_error}") from e
        else:
            # Propagate error when JSON failed or fallback is disabled
            raise RuntimeError(f"Provider initialization failed without fallback: {e}") from e


def get_provider_status() -> dict:
    """
    Get the current provider configuration and status.
    
    Returns:
        Dictionary with provider info, configuration, and health status
    """
    try:
        cfg = ProviderConfig()
        provider = get_market_data_provider(cfg)
        health = provider.health_check()
        
        return {
            "provider_type": cfg.provider,
            "provider_name": provider.get_provider_name(),
            "symbols_count": len(ProviderConfig.DEFAULT_SYMBOLS),
            "live_simulation": cfg.live_sim,
            "json_file": ProviderConfig.get_json_file_path(),
            "health": health,
            "status": "ok"
        }
    except Exception as e:
        return {
            "provider_type": os.getenv("DATA_PROVIDER", "json"),
            "error": str(e),
            "status": "error"
        }

# Cache the provider so the polling thread persists (for the config-driven path)
_CACHED_PROVIDER = None
_CACHED_CONFIG_SNAPSHOT = None


def _config_snapshot(config: ProviderConfig) -> tuple:
    return (
        config.provider,
        config.excel_file,
        config.excel_sheet,
        config.excel_range,
        config.excel_live,
        config.live_sim,
    )


def get_market_data_provider(config: ProviderConfig):
    """Return a provider instance based on the request/env-driven ProviderConfig.

    This function prefers Excel Live when config.excel_live is true. If Excel Live
    cannot initialize (e.g., xlwings missing or Excel not available), it falls
    back to the file-based ExcelProvider. Other provider types (json, schwab)
    are delegated to the create_provider factory.
    """
    global _CACHED_PROVIDER, _CACHED_CONFIG_SNAPSHOT

    snap = _config_snapshot(config)
    if _CACHED_PROVIDER is not None and _CACHED_CONFIG_SNAPSHOT == snap:
        return _CACHED_PROVIDER

    provider: BaseProvider

    if config.provider in ("excel", "excel_live"):
        excel_file = config.excel_file or ProviderConfig.get_excel_file_path()
        sheet = config.excel_sheet or "Futures"

        if config.excel_live:
            # Try Excel Live first; on failure, fall back to file-based Excel
            try:
                prov_live = ExcelLiveProvider(
                    file_path=excel_file,
                    sheet_name=sheet,
                    range_address=config.excel_range or "A1:M20",
                    poll_ms=200,
                    require_open=os.getenv("EXCEL_LIVE_REQUIRE_OPEN", "0").lower() in ("1", "true", "yes", "on"),
                )
                prov_live.start()
                provider = prov_live
            except Exception as e:
                print(f"Excel Live initialization failed: {e}\nFalling back to Excel file provider (openpyxl).")
                provider = create_provider(
                    "excel", excel_file=excel_file, sheet_name=sheet, live_simulation=False
                )
        else:
            provider = create_provider(
                "excel", excel_file=excel_file, sheet_name=sheet, live_simulation=False
            )

    elif config.provider == "json":
        json_file = ProviderConfig.get_json_file_path()
        provider = create_provider("json", json_file=json_file, live_simulation=config.live_sim)

    elif config.provider == "schwab":
        # Construct minimal config; SchwabProvider currently raises NotImplemented
        schwab_config = {
            "client_id": os.getenv("SCHWAB_CLIENT_ID"),
            "client_secret": os.getenv("SCHWAB_CLIENT_SECRET"),
            "base_url": os.getenv("SCHWAB_BASE_URL", "https://api.schwabapi.com"),
            "scopes": os.getenv("SCHWAB_SCOPES", "read").split(","),
        }
        provider = create_provider("schwab", config=schwab_config)

    else:
        # Default to JSON to remain functional
        json_file = ProviderConfig.get_json_file_path()
        provider = create_provider("json", json_file=json_file, live_simulation=True)

    _CACHED_PROVIDER = provider
    _CACHED_CONFIG_SNAPSHOT = snap
    return provider