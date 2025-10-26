"""
Market Open Grading Service

Monitors pending MarketOpenSession trades and grades them in real-time.
Runs every 0.5 seconds to check if all 11 futures hit target or stop.
"""

import time
import logging
from decimal import Decimal
from django.utils import timezone
from FutureTrading.models.MarketOpen import MarketOpenSession, FutureSnapshot
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


class MarketOpenGrader:
    """
    Grades pending market open trades by monitoring all 11 futures prices.
    Checks every 0.5 seconds if target or stop is hit for each future.
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
            # Get latest quote from Redis snapshot
            data = live_data_redis.get_latest_quote(symbol)
            
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
    
    def grade_future_snapshot(self, snapshot):
        """
        Check if a future snapshot's theoretical trade has hit target or stop.
        
        Args:
            snapshot: FutureSnapshot instance
            
        Returns:
            bool: True if graded (outcome determined), False if still pending
        """
        # Skip if already graded or TOTAL or no entry/signal
        if snapshot.outcome != 'PENDING' or snapshot.symbol == 'TOTAL':
            return True
        
        if not snapshot.entry_price or not snapshot.signal or not snapshot.high_dynamic or not snapshot.low_dynamic:
            return True  # Can't grade without complete data
        
        # Skip HOLD signals
        if snapshot.signal == 'HOLD':
            snapshot.outcome = 'NEUTRAL'
            snapshot.save(update_fields=['outcome'])
            return True
        
        # Get current price
        current_price = self.get_current_price(snapshot.symbol, snapshot.signal)
        
        if not current_price:
            return False  # Can't grade without price data
        
        # Check if target or stop is hit
        worked = False
        didnt_work = False
        
        if snapshot.signal in ['BUY', 'STRONG_BUY']:
            # For BUY: target = high_dynamic, stop = low_dynamic
            if current_price >= snapshot.high_dynamic:
                worked = True
            elif current_price <= snapshot.low_dynamic:
                didnt_work = True
                
        elif snapshot.signal in ['SELL', 'STRONG_SELL']:
            # For SELL: target = low_dynamic, stop = high_dynamic
            if current_price <= snapshot.low_dynamic:
                worked = True
            elif current_price >= snapshot.high_dynamic:
                didnt_work = True
        
        # Update outcome if determined
        if worked:
            snapshot.outcome = 'WORKED'
            snapshot.exit_price = current_price
            snapshot.exit_time = timezone.now()
            snapshot.save(update_fields=['outcome', 'exit_price', 'exit_time'])
            logger.info(f"✅ {snapshot.symbol} WORKED - Exit: {current_price}")
            return True
            
        elif didnt_work:
            snapshot.outcome = 'DIDNT_WORK'
            snapshot.exit_price = current_price
            snapshot.exit_time = timezone.now()
            snapshot.save(update_fields=['outcome', 'exit_price', 'exit_time'])
            logger.info(f"❌ {snapshot.symbol} DIDN'T WORK - Stop: {current_price}")
            return True
        
        return False  # Still pending
    
    def grade_session(self, session):
        """
        Check if a session's YM trade has hit target or stop.
        Also updates the session based on YM snapshot outcome.
        
        Args:
            session: MarketOpenSession instance
            
        Returns:
            bool: True if graded (outcome determined), False if still pending
        """
        # Skip if already graded or no entry price
        if session.fw_nwdw != 'PENDING' or not session.ym_entry_price:
            return True
        
        # Skip HOLD signals (no trade to grade)
        if session.total_signal == 'HOLD':
            session.fw_nwdw = 'NEUTRAL'
            session.save(update_fields=['fw_nwdw', 'updated_at'])
            logger.info(f"Session {session.id} marked NEUTRAL (HOLD signal)")
            return True
        
        # Get current YM price
        current_price = self.get_current_price('YM', session.total_signal)
        
        if not current_price:
            return False  # Can't grade without price data
        
        # Check if target or stop is hit
        worked = False
        didnt_work = False
        
        if session.total_signal in ['BUY', 'STRONG_BUY']:
            # For BUY: target = high_dynamic, stop = low_dynamic
            if current_price >= session.ym_high_dynamic:
                worked = True
            elif current_price <= session.ym_low_dynamic:
                didnt_work = True
                
        elif session.total_signal in ['SELL', 'STRONG_SELL']:
            # For SELL: target = low_dynamic, stop = high_dynamic
            if current_price <= session.ym_low_dynamic:
                worked = True
            elif current_price >= session.ym_high_dynamic:
                didnt_work = True
        
        # Update outcome if determined
        if worked:
            session.fw_nwdw = 'WORKED'
            session.didnt_work = False
            session.fw_exit_value = current_price
            session.save(update_fields=['fw_nwdw', 'didnt_work', 'fw_exit_value', 'updated_at'])
            logger.info(f"✅ Session {session.id} (YM) WORKED - Exit: {current_price}")
            return True
            
        elif didnt_work:
            session.fw_nwdw = 'DIDNT_WORK'
            session.didnt_work = True
            session.fw_stopped_out_value = current_price
            session.fw_stopped_out_nwdw = 'STOPPED_OUT'
            session.save(update_fields=[
                'fw_nwdw', 'didnt_work', 'fw_stopped_out_value', 
                'fw_stopped_out_nwdw', 'updated_at'
            ])
            logger.info(f"❌ Session {session.id} (YM) DIDN'T WORK - Stop: {current_price}")
            return True
        
        return False  # Still pending
    
    def run_grading_loop(self):
        """
        Main grading loop - runs continuously, checking every 0.5 seconds.
        Grades all pending sessions and their future snapshots.
        """
        logger.info(f"Starting Market Open Grader (check interval: {self.check_interval}s)")
        self.running = True
        
        while self.running:
            try:
                # Get all pending sessions
                pending_sessions = MarketOpenSession.objects.filter(fw_nwdw='PENDING')
                
                # Get all pending future snapshots
                pending_snapshots = FutureSnapshot.objects.filter(outcome='PENDING').exclude(symbol='TOTAL')
                
                if pending_sessions.exists() or pending_snapshots.exists():
                    logger.debug(f"Grading {pending_sessions.count()} sessions and {pending_snapshots.count()} futures...")
                    
                    # Grade sessions (YM actual trades)
                    for session in pending_sessions:
                        self.grade_session(session)
                    
                    # Grade all future snapshots (theoretical trades for analytics)
                    for snapshot in pending_snapshots:
                        self.grade_future_snapshot(snapshot)
                
                # Wait before next check
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("Grading loop interrupted by user")
                self.running = False
                break
                
            except Exception as e:
                logger.error(f"Error in grading loop: {e}", exc_info=True)
                time.sleep(self.check_interval)  # Continue after error
    
    def stop(self):
        """Stop the grading loop"""
        logger.info("Stopping Market Open Grader...")
        self.running = False


# Singleton instance
grader = MarketOpenGrader()


def start_grading_service():
    """Start the grading service (call from management command or background task)"""
    grader.run_grading_loop()


def stop_grading_service():
    """Stop the grading service"""
    grader.stop()
