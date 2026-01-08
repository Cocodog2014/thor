"""Active markets utility for futures and trading (compatibility shim)."""

from typing import Optional, Set, List


def get_control_countries(require_session_capture: bool = False) -> Optional[List[str]]:
    """
    Get list of control (primary) countries for trading.
    
    Args:
        require_session_capture: If True, only return countries with session capture configured.
                                If False, return all configured countries.
    
    Returns:
        List of 2-letter country codes, or empty list if none configured.
    """
    from GlobalMarkets.models import Market
    
    # Get countries from active markets
    countries = set()
    markets = Market.objects.filter(is_active=True)
    
    if require_session_capture:
        # Filter to markets with at least one session
        markets = markets.annotate(
            session_count=__import__('django.db.models', fromlist=['Count']).Count('sessions')
        ).filter(session_count__gt=0)
    
    for market in markets:
        if market.key:
            # Use market key as country code (e.g., "US", "GB", etc.)
            countries.add(market.key.upper())
    
    # Fallback to defaults if no markets configured
    if not countries:
        countries = {"US", "GB", "DE", "FR", "JP", "AU", "CA"}
    
    return sorted(list(countries))


def get_control_markets(statuses: Optional[Set[str]] = None):
    """
    Get control markets for futures trading (shim for ThorTrading compatibility).
    
    Args:
        statuses: Optional set of statuses to filter by (e.g., {"OPEN"})
        
    Returns:
        Queryset of active Market objects. Can be empty if no markets configured.
    """
    from GlobalMarkets.models import Market
    
    # Return all active markets that have sessions configured
    qs = Market.objects.filter(is_active=True).prefetch_related("sessions")
    
    if statuses:
        # Filter by status if provided
        qs = qs.filter(status__in=statuses)
    
    return qs
