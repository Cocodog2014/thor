"""Active markets utility for futures and trading (compatibility shim)."""

from typing import Optional, Set


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
