"""
GlobalMarkets signals

Triggers market open capture when market status changes.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Market

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Market)
def on_market_status_change(sender, instance, created, **kwargs):
    """
    Signal handler for Market status changes.
    Triggers market open capture when status changes to OPEN.
    """
    # Don't trigger on initial creation
    if created:
        return
    
    # Only trigger if status is OPEN and market is active
    if instance.status == 'OPEN' and instance.is_active:
        # Check if this is an actual status change (not just a save)
        # We'll import here to avoid circular imports
        try:
            from FutureTrading.views.MarketOpenCapture import capture_market_open
            
            logger.info(f"🔔 Market {instance.country} opened - triggering capture...")
            
            # Trigger the capture
            session = capture_market_open(instance)
            
            if session:
                logger.info(f"✅ Market open captured for {instance.country} - Session #{session.session_number}")
            else:
                logger.warning(f"⚠️ Failed to capture market open for {instance.country}")
                
        except Exception as e:
            logger.error(f"❌ Error triggering market open capture for {instance.country}: {e}", exc_info=True)
