"""
Market Open Grading Logic (SIMPLIFIED)

Grades MarketSession rows in real time based on entry/target prices.

What this does:
- Watches all MarketSession rows with wndw='PENDING'.
- For each row, reads the current bid/ask from Redis.
- For BUY/STRONG_BUY:
    - If price >= target_high  -> wndw = 'WORKED'
    - If price <= target_low   -> wndw = 'DIDNT_WORK'
- For SELL/STRONG_SELL:
    - If price <= target_low   -> wndw = 'WORKED'
    - If price >= target_high  -> wndw = 'DIDNT_WORK'
- For HOLD or missing targets, marks wndw='NEUTRAL' and skips grading.

Notes:
- Uses only the current MarketSession schema: wndw, bhs, entry_price, target_high, target_low.
- Does NOT store detailed exit price/timestamps; that can move into a dedicated
  TradeOutcome / BacktestResult model later if needed.
"""

import time
import logging
from decimal import Decimal

from FutureTrading.models.MarketSession import MarketSession
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


class MarketGrader:
    """
    Grades pending market open trades for each future.

    Single-table design: one MarketSession row per future per market open.
    Checks every `check_interval` seconds whether each pending trade has hit
    its target or stop.
    """

    def __init__(self, check_interval: float = 0.5):
        """
        Initialize grader.

        Args:
            check_interval: Seconds between checks (default 0.5)
        """
        self.check_interval = check_interval
        self.running = False

    # -------------------------
    # Data access / price lookup
    # -------------------------

    def get_current_price(self, symbol: str, signal: str) -> Decimal | None:
        """
        Get current price from Redis for any symbol.

        - For BUY/STRONG_BUY: use bid (we exit at bid).
        - For SELL/STRONG_SELL: use ask (we exit at ask).
        - For HOLD: returns None (no trade to grade).

        Handles DX -> $DXY mapping for Redis.
        """
        try:
            redis_key = '$DXY' if symbol == 'DX' else symbol
            data = live_data_redis.get_latest_quote(redis_key)

            if not data:
                logger.warning("No %s data in Redis snapshot", symbol)
                return None

            if signal in ['BUY', 'STRONG_BUY']:
                price = data.get('bid')
            elif signal in ['SELL', 'STRONG_SELL']:
                price = data.get('ask')
            else:
                # HOLD or unknown signal -> nothing to grade
                return None

            return Decimal(str(price)) if price is not None else None

        except Exception as e:
            logger.error("Error getting %s price from Redis: %s", symbol, e, exc_info=True)
            return None

    # --------------
    # Grading logic
    # --------------

    def grade_session(self, session: MarketSession) -> bool:
        """
        Check if a session's trade has hit target or stop.

        Args:
            session: MarketSession instance (one future)

        Returns:
            bool: True if graded (wndw resolved), False if still pending
        """
        # Skip if already graded
        if session.wndw != 'PENDING':
            return True

        # TOTAL composite row: no actual trade, mark neutral once and move on
        if session.future == 'TOTAL':
            session.wndw = 'NEUTRAL'
            session.save(update_fields=['wndw', 'updated_at'])
            return True

        # Skip if no entry price or no targets
        if not session.entry_price or not session.target_high or not session.target_low:
            # No way to grade this row; mark NEUTRAL so it doesn't keep clogging pending
            session.wndw = 'NEUTRAL'
            session.save(update_fields=['wndw', 'updated_at'])
            return True

        # Skip HOLD or blank signals: treat as neutral
        if session.bhs in ['HOLD', None, '']:
            session.wndw = 'NEUTRAL'
            session.save(update_fields=['wndw', 'updated_at'])
            return True

        # Get current price
        current_price = self.get_current_price(session.future, session.bhs)
        if current_price is None:
            # Can't grade without price data
            return False

        worked = False
        didnt_work = False

        # BUY side logic
        if session.bhs in ['BUY', 'STRONG_BUY']:
            # Target = target_high, Stop = target_low
            if current_price >= session.target_high:
                worked = True
            elif current_price <= session.target_low:
                didnt_work = True

        # SELL side logic
        elif session.bhs in ['SELL', 'STRONG_SELL']:
            # Target = target_low, Stop = target_high
            if current_price <= session.target_low:
                worked = True
            elif current_price >= session.target_high:
                didnt_work = True

        # Update wndw based on result
        if worked:
            session.wndw = 'WORKED'
            session.save(update_fields=['wndw', 'updated_at'])
            logger.info(
                "✅ %s (Session #%s) WORKED at ~%s",
                session.future, session.session_number, current_price
            )
            return True

        if didnt_work:
            session.wndw = 'DIDNT_WORK'
            session.save(update_fields=['wndw', 'updated_at'])
            logger.info(
                "❌ %s (Session #%s) DIDN'T WORK at ~%s",
                session.future, session.session_number, current_price
            )
            return True

        return False  # Still pending

    # ----------------
    # Grading main loop
    # ----------------

    def run_grading_loop(self):
        """
        Main grading loop - runs continuously, checking every `check_interval` seconds.

        Grades all pending MarketSession rows (wndw='PENDING').
        """
        logger.info("Starting Market Open Grader (interval: %ss)", self.check_interval)
        self.running = True

        while self.running:
            try:
                pending_sessions = MarketSession.objects.filter(wndw='PENDING')

                if pending_sessions.exists():
                    logger.debug("Grading %d pending sessions...", pending_sessions.count())

                    for session in pending_sessions:
                        self.grade_session(session)

                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("Grading loop interrupted by user")
                self.running = False
                break

            except Exception as e:
                logger.error("Error in grading loop: %s", e, exc_info=True)
                time.sleep(self.check_interval)

        logger.info("Market Open Grader stopped")

    def stop(self):
        """Stop the grading loop."""
        logger.info("Stopping Market Open Grader...")
        self.running = False


# Singleton instance
grader = MarketGrader()


def start_grading_service():
    """Start the grading service (call from management command or background task)."""
    grader.run_grading_loop()


def stop_grading_service():
    """Stop the grading service."""
    grader.stop()


__all__ = ['start_grading_service', 'stop_grading_service', 'MarketGrader']

