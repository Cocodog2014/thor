"""
Views for SchwabLiveData

This module provides API endpoints that use the provider system to serve
market data. It integrates with the existing futuretrading app's signal
and statistical value system.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.http import HttpResponseRedirect
from typing import List, Dict, Any
import logging
import json

from .provider_factory import ProviderConfig, get_market_data_provider, get_provider_status
from FutureTrading.models import SignalStatValue, ContractWeight
from .schwab_client import SchwabApiClient

logger = logging.getLogger(__name__)


class SchwabQuotesView(APIView):
    """
    API endpoint for fetching latest market quotes using the provider system.
    
    This view:
    1. Uses the configured provider (JSON or Schwab) to get market data
    2. Enriches the data with signal stat values from the database
    3. Applies contract weights for composite calculations
    4. Returns data in the same format as the existing LatestQuotesView
    """
    
    def get(self, request):
        """
        Get latest quotes for all configured futures.
        """
        try:
            # Build config from request (query params override env inside ProviderConfig)
            cfg = ProviderConfig(request)

            # Never simulate for Excel sources
            if cfg.provider in ("excel", "excel_live"):
                cfg.live_sim = False

            # Get provider instance
            provider = get_market_data_provider(cfg)

            # Fetch quotes with default symbols (support dict with 'rows' or direct list)
            symbols = ProviderConfig.DEFAULT_SYMBOLS
            raw = provider.get_latest_quotes(symbols)
            raw_quotes = raw.get("rows", raw) if isinstance(raw, dict) else raw

            # Enrich with DB values (signals/weights)
            enriched_quotes = self._enrich_quotes_with_db_values(raw_quotes)

            # Composite
            total_data = self._calculate_composite_total(enriched_quotes)

            # Provider info helpers (safe defaults)
            get_name = getattr(provider, "get_provider_name", lambda: provider.__class__.__name__)
            get_health = getattr(provider, "health_check", lambda: {})

            return Response({
                "rows": enriched_quotes,
                "total": total_data,
                "provider_info": {
                    "name": get_name(),
                    "health": get_health(),
                }
            })

        except NotImplementedError as e:
            logger.error(f"Provider not implemented: {e}")
            return Response({"error": str(e)}, status=status.HTTP_501_NOT_IMPLEMENTED)
        except Exception as e:
            logger.error(f"Error fetching quotes: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _enrich_quotes_with_db_values(self, raw_quotes: List[Dict]) -> List[Dict]:
        """
        Enrich raw provider quotes with database signal and weight values.
        
        Args:
            raw_quotes: Raw quotes from provider
            
        Returns:
            Enriched quotes with database values merged in
        """
        enriched = []
        
        def _safe_float(val, default: float) -> float:
            try:
                if val is None:
                    return default
                # Provider may send strings; handle 'None' and blanks gracefully
                if isinstance(val, str):
                    s = val.strip()
                    if s == '' or s.lower() == 'none':
                        return default
                    return float(s)
                return float(val)
            except Exception:
                return default

        for quote in raw_quotes:
            symbol = quote["instrument"]["symbol"]
            
            # Get signal from provider (fallback to database)
            provider_signal = quote.get("extended_data", {}).get("signal")
            
            # Look up stat value from database
            try:
                signal_stat = SignalStatValue.objects.get(
                    instrument__symbol=symbol,
                    signal=provider_signal
                )
                db_stat_value = float(signal_stat.value)  # Use 'value' not 'stat_value'
            except SignalStatValue.DoesNotExist:
                # Use provider value as fallback, but parse safely
                db_stat_value = _safe_float(quote.get("extended_data", {}).get("stat_value", 0.0), 0.0)
            
            # Look up contract weight from database
            try:
                contract_weight_obj = ContractWeight.objects.get(instrument__symbol=symbol)
                db_contract_weight = float(contract_weight_obj.weight)
            except ContractWeight.DoesNotExist:
                # Use provider value as fallback, but parse safely
                db_contract_weight = _safe_float(quote.get("extended_data", {}).get("contract_weight", 1.0), 1.0)
            
            # Update extended_data with database values
            quote["extended_data"].update({
                "stat_value": str(db_stat_value),
                "contract_weight": str(db_contract_weight)
            })
            
            enriched.append(quote)
        
        return enriched
    
    def _calculate_composite_total(self, quotes: List[Dict]) -> Dict[str, Any]:
        """
        Calculate weighted composite total from all quotes.
        
        Args:
            quotes: List of enriched quote dictionaries
            
        Returns:
            Composite total data dictionary
        """
        sum_weighted = 0.0
        total_weights = 0.0
        count = 0
        
        for quote in quotes:
            try:
                stat_value = float(quote["extended_data"]["stat_value"])
                weight = float(quote["extended_data"]["contract_weight"])
                
                sum_weighted += stat_value * weight
                total_weights += abs(weight)
                count += 1
                
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Error processing quote {quote.get('instrument', {}).get('symbol')}: {e}")
                continue
        
        # Calculate weighted average
        avg_weighted = sum_weighted / total_weights if total_weights > 0 else 0.0
        
        return {
            "sum_weighted": f"{sum_weighted:.2f}",
            "avg_weighted": f"{avg_weighted:.3f}",
            "count": count,
            "denominator": f"{total_weights:.2f}",
            "as_of": quotes[0]["timestamp"] if quotes else None
        }


class ProviderStatusView(APIView):
    """
    API endpoint for checking provider status and configuration.
    
    Useful for debugging and monitoring which provider is active.
    """
    
    def get(self, request):
        """Get current provider status and configuration."""
        try:
            cfg = ProviderConfig(request)
            provider_status = get_provider_status(cfg)
            return Response(provider_status)
        except Exception as e:
            logger.error(f"Error getting provider status: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProviderHealthView(APIView):
    """
    Simple health check endpoint for the provider system.
    """
    
    def get(self, request):
        """Basic health check for the provider system."""
        try:
            cfg = ProviderConfig(request)
            provider = get_market_data_provider(cfg)
            health = provider.health_check()
            
            return Response({
                "status": "healthy" if health.get("connected") else "unhealthy",
                "provider": provider.get_provider_name(),
                "details": health
            })
        except Exception as e:
            return Response({
                "status": "unhealthy",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Legacy function-based view for compatibility
def schwab_quotes_legacy(request):
    """
    Legacy function-based view that wraps the class-based view.
    Can be used if you prefer function-based views.
    """
    view = SchwabQuotesView()
    return view.get(request)

def latest_quotes(request):
    cfg = ProviderConfig(request)
    if cfg.provider in ("excel", "excel_live"):
        cfg.live_sim = False
    provider = get_market_data_provider(cfg)
    symbols = ProviderConfig.DEFAULT_SYMBOLS
    data = provider.get_latest_quotes(symbols)
    return JsonResponse(data, safe=False)

# Check for fallbacks to JSON data
def get_quotes(request):
    """
    Get latest quotes from the provider.
    """
    try:
        cfg = ProviderConfig(request)
        provider = get_market_data_provider(cfg)
        symbols = ProviderConfig.DEFAULT_SYMBOLS
        data = provider.get_latest_quotes(symbols)
        return JsonResponse(data, safe=False)
    except Exception as e:
        # No JSON fallback, just return the error
        logger.error(f"Error fetching quotes: {e}", exc_info=True)
        return JsonResponse(
            {"error": f"Provider error: {str(e)}"}, 
            status=500
        )


# --- OAuth flow endpoints ---
def schwab_auth_start(request):
    """Begin Schwab OAuth by redirecting to provider's authorization URL.

    This only constructs the URL; token exchange is not implemented yet.
    """
    try:
        client = SchwabApiClient()
        url = client.build_authorization_url(state="thor")
        return HttpResponseRedirect(url)
    except Exception as e:
        logger.error(f"Auth start error: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def schwab_auth_callback(request):
    """Handle the OAuth redirect from Schwab.

    For now, we simply echo the 'code' and 'state' so we can verify wiring.
    """
    try:
        code = request.GET.get("code")
        state = request.GET.get("state")
        error = request.GET.get("error")
        if error:
            return JsonResponse({"received": True, "error": error, "state": state}, status=400)
        if not code:
            return JsonResponse({"received": False, "error": "missing code"}, status=400)

        client = SchwabApiClient()
        result = client.exchange_code_for_token(code)
        return JsonResponse({
            "received": True,
            "token_exchange": result,
            "connected": True,
        })
    except Exception as e:
        logger.error(f"Callback error: {e}")
        return JsonResponse({"error": str(e)}, status=500)
