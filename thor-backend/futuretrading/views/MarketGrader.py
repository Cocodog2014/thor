"""
Market Open Grading Logic (DISABLED)

This module is intentionally disabled as part of the MarketSession schema
simplification. The previous implementation depended on legacy grading
columns that no longer exist on `MarketSession` (e.g., outcome, wndw,
didnt_work, exit_price, exit_time, fw_exit_value, fw_stopped_out_value,
fw_stopped_out_nwdw).

Why disabled now:
- The new design treats `MarketSession` as a snapshot of "what happened at open".
- Grading/backtesting belongs in a dedicated model (e.g., TradeOutcome or
    BacktestResult) rather than reusing MarketSession.

Next steps to re-enable:
- Design and migrate a new backtest/outcome model to store grading results.
- Update this module to write to that model instead of MarketSession.

Until then, any attempt to start the grading loop will raise NotImplementedError.
"""

import time
import logging
from decimal import Decimal
from django.utils import timezone
from FutureTrading.models.MarketSession import MarketSession
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)

DISABLED_REASON = (
    "MarketGrader is disabled: MarketSession no longer has grading columns. "
    "Implement a dedicated Backtest/TradeOutcome model and update the grader to use it."
)


class MarketGrader:
    """
    Grades pending market open trades for each future.
    Single-table design: one session row per future per market open.
    Checks every 0.5 seconds if target or stop is hit.
    """
    
    def __init__(self, check_interval=0.5):
        """
        Initialize grader.
        
        Args:
            check_interval: Seconds between checks (default 0.5)
        """
        self.check_interval = check_interval
        self.running = False
    
    def get_current_price(self, symbol, signal):
        """
        Get current price from Redis for any symbol (bid if selling, ask if buying).
        
        Args:
            symbol: Future symbol (YM, ES, NQ, etc.)
            signal: The trade signal (BUY/SELL/STRONG_BUY/STRONG_SELL/HOLD)
            
        Returns:
            Decimal: Current price to compare against targets
        """
        try:
            # Handle DX -> $DXY mapping
            redis_key = '$DXY' if symbol == 'DX' else symbol
            data = live_data_redis.get_latest_quote(redis_key)
            
            if not data:
                logger.warning(f"No {symbol} data in Redis snapshot")
                return None
            
            # Use bid if we bought (we exit at bid), ask if we sold (we exit at ask)
            if signal in ['BUY', 'STRONG_BUY']:
                price = data.get('bid')
            elif signal in ['SELL', 'STRONG_SELL']:
                price = data.get('ask')
            else:  # HOLD
                return None
            
            return Decimal(str(price)) if price else None
            
        except Exception as e:
            logger.error(f"Error getting {symbol} price from Redis: {e}")
            return None
    
    def grade_session(self, session):
        """
        Check if a session's trade has hit target or stop.
        Works for individual futures AND TOTAL row.
        
        Args:
            session: MarketSession instance (one future)
            
        Returns:
            bool: True if graded (outcome determined), False if still pending
        """
        # Skip if already graded
        if session.outcome != 'PENDING' and session.wndw != 'PENDING':
            return True
        
        # Skip TOTAL composite rows (no actual trade)
        if session.future == 'TOTAL':
            if session.outcome == 'PENDING':
                session.outcome = 'NEUTRAL'
                session.wndw = 'NEUTRAL'
                session.save(update_fields=['outcome', 'wndw', 'updated_at'])
            return True
        
        # Skip if no entry price or targets
        if not session.entry_price or not session.target_high or not session.target_low:
            return True  # Can't grade without complete data
        
        # Skip HOLD signals
        if session.bhs == 'HOLD' or not session.bhs:
            if session.outcome == 'PENDING':
                session.outcome = 'NEUTRAL'
                session.wndw = 'NEUTRAL'
                session.save(update_fields=['outcome', 'wndw', 'updated_at'])
            return True
        
        # Get current price for this future
        current_price = self.get_current_price(session.future, session.bhs)
        
        if not current_price:
            return False  # Can't grade without price data
        
        # Check if target or stop is hit
        worked = False
        didnt_work = False
        
        if session.bhs in ['BUY', 'STRONG_BUY']:
            # For BUY: target = target_high, stop = target_low
            if current_price >= session.target_high:
                worked = True
            elif current_price <= session.target_low:
                didnt_work = True
                
        elif session.bhs in ['SELL', 'STRONG_SELL']:
            # For SELL: target = target_low, stop = target_high
            if current_price <= session.target_low:
                worked = True
            elif current_price >= session.target_high:
                didnt_work = True
        
        # Update outcome if determined
        if worked:
            session.outcome = 'WORKED'
            session.wndw = 'WORKED'
            session.didnt_work = False
            session.exit_price = current_price
            session.exit_time = timezone.now()
            session.fw_exit_value = current_price
            session.save(update_fields=[
                    'outcome', 'wndw', 'didnt_work', 'exit_price', 
                'exit_time', 'fw_exit_value', 'updated_at'
            ])
            logger.info(f"✅ {session.future} (Session #{session.session_number}) WORKED - Exit: {current_price}")
            return True
            
        elif didnt_work:
            session.outcome = 'DIDNT_WORK'
            session.wndw = 'DIDNT_WORK'
            session.didnt_work = True
            session.exit_price = current_price
            session.exit_time = timezone.now()
            session.fw_stopped_out_value = current_price
            session.fw_stopped_out_nwdw = 'STOPPED_OUT'
            session.save(update_fields=[
                    'outcome', 'wndw', 'didnt_work', 'exit_price', 'exit_time',
                'fw_stopped_out_value', 'fw_stopped_out_nwdw', 'updated_at'
            ])
            logger.info(f"❌ {session.future} (Session #{session.session_number}) DIDN'T WORK - Stop: {current_price}")
            return True
        
        return False  # Still pending
    
    def run_grading_loop(self):
        """Disabled entry point for the grading loop."""
        logger.warning(DISABLED_REASON)
        raise NotImplementedError(DISABLED_REASON)
    
    def stop(self):
        """Stop the grading loop"""
        logger.info("Stopping Market Open Grader...")
        self.running = False


# Singleton instance
grader = MarketGrader()


def start_grading_service():
    """Start the grading service (disabled)."""
    logger.warning(DISABLED_REASON)
    raise NotImplementedError(DISABLED_REASON)


def stop_grading_service():
    """Stop the grading service (no-op while disabled)."""
    try:
        grader.stop()
    except Exception:
        pass


__all__ = ['start_grading_service', 'stop_grading_service', 'MarketGrader']
