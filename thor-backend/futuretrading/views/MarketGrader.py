"""
Market Open Grading Logic (SIMPLIFIED)

This module continuously checks all MarketSession rows where wndw='PENDING'
and determines whether each trade has:

- Hit the target  →  WORKED
- Hit the stop    →  DIDNT_WORK
- Had no trade setup → NEUTRAL

The grader uses:
- entry_price
- target_high
- target_low
- bhs (BUY/HOLD/SELL)
- live price data from Redis (bid/ask)

The grader does NOT:
- Store exit timestamps
- Store exit prices
(Those can be added later in a TradeOutcome model.)
"""

import time
import logging
from decimal import Decimal

from FutureTrading.models.MarketSession import MarketSession
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)


class MarketGrader:
    """
    MarketGrader continuously evaluates open trades for ALL futures.

    HOW IT WORKS:
    -------------
    - Every .5 seconds (or whatever interval you set), it scans all
      MarketSession rows with wndw='PENDING'.

    - For each row:
        * Fetches the current exit price from Redis.
        * Compares the price against target_high/target_low.
        * Updates wndw to:
            'WORKED'      — target reached
            'DIDNT_WORK'  — stop reached
            'NEUTRAL'     — no valid trade or HOLD signal

    - TOTAL is treated like a normal trade, but its price source is YM.
    """

    def __init__(self, check_interval: float = 0.5):
        """
        Args:
            check_interval (float): seconds between grading cycles.
        """
        self.check_interval = check_interval
        self.running = False

    # ============================================================
    # DATA ACCESS / PRICE LOOKUP
    # ============================================================

    def get_current_price(self, symbol: str, signal: str) -> Decimal | None:
        """
        Fetch the live price used for EXIT logic.

        EXIT PRICE RULES:
        -----------------
        BUY / STRONG_BUY  → exit at BID  (market sells to bid)
        SELL / STRONG_SELL → exit at ASK (market buys to ask)
        HOLD               → no exit (no trade)

        SYMBOL MAPPING:
        ---------------
        TOTAL → '/YM'   (system trade executed using YM quotes)
        DX    → '$DXY'  (your live feed provides DXY index, not DX futures)
        ALL OTHERS → use the symbol as-is.

        Returns:
            Decimal price or None if unavailable.
        """
        try:
            # Map special synthetic symbols to live Redis keys.
            if symbol == 'TOTAL':
                # TOTAL is graded using YM price
                redis_key = '/YM'
            elif symbol == 'DX':
                # DX is graded using DXY index because DX futures aren't fed
                redis_key = '$DXY'
            else:
                # All other futures use their own symbol
                redis_key = symbol

            data = live_data_redis.get_latest_quote(redis_key)

            if not data:
                logger.warning("No Redis data for %s (mapped key: %s)", symbol, redis_key)
                return None

            # Exit price selection depends on direction of trade
            if signal in ['BUY', 'STRONG_BUY']:
                price = data.get('bid')  # we exit longs on the bid
            elif signal in ['SELL', 'STRONG_SELL']:
                price = data.get('ask')  # we exit shorts on the ask
            else:
                # HOLD or invalid = not a trade
                return None

            return Decimal(str(price)) if price is not None else None

        except Exception as e:
            logger.error("Redis price error for %s: %s", symbol, e, exc_info=True)
            return None

    # ============================================================
    # CORE GRADING LOGIC
    # ============================================================

    def grade_session(self, session: MarketSession) -> bool:
        """
        Evaluate a single MarketSession row.

        The row is graded if:
            - It has a valid entry_price
            - It has valid target_high/target_low
            - It is not HOLD
            - A valid exit price exists from Redis

        Returns:
            True if the row is no longer PENDING (graded or neutral)
            False if still pending (unable to evaluate this cycle)
        """

        # Already graded → nothing to do
        if session.wndw != 'PENDING':
            return True

        # If no entry or missing targets → cannot grade → mark NEUTRAL
        if not session.entry_price or not session.target_high or not session.target_low:
            session.wndw = 'NEUTRAL'
            session.save(update_fields=['wndw'])
            return True

        # HOLD (or empty signal) → no trade → mark NEUTRAL
        if session.bhs in ['HOLD', None, '']:
            session.wndw = 'NEUTRAL'
            session.save(update_fields=['wndw'])
            return True

        # Get current price for exit evaluation
        current_price = self.get_current_price(session.future, session.bhs)
        if current_price is None:
            # Cannot grade without a live price
            return False

        worked = False
        didnt_work = False

        # LONG LOGIC (BUY / STRONG_BUY)
        if session.bhs in ['BUY', 'STRONG_BUY']:
            target = session.target_high
            stop = session.target_low

            if current_price >= target:
                worked = True
            elif current_price <= stop:
                didnt_work = True

        # SHORT LOGIC (SELL / STRONG_SELL)
        elif session.bhs in ['SELL', 'STRONG_SELL']:
            target = session.target_low
            stop = session.target_high

            if current_price <= target:
                worked = True
            elif current_price >= stop:
                didnt_work = True

        # Save result
        if worked:
            session.wndw = 'WORKED'
            session.save(update_fields=['wndw'])
            logger.info(
                "✅ %s (Session #%s) WORKED at ~%s",
                session.future, session.session_number, current_price
            )
            return True

        if didnt_work:
            session.wndw = 'DIDNT_WORK'
            session.save(update_fields=['wndw'])
            logger.info(
                "❌ %s (Session #%s) DIDN'T WORK at ~%s",
                session.future, session.session_number, current_price
            )
            return True

        # Still inside target/stop range → pending
        return False

    # ============================================================
    # GRADING LOOP
    # ============================================================

    def run_grading_loop(self):
        """
        The continuous loop that powers the whole grading engine.

        - Runs forever (until stop() called)
        - Every interval:
            * Fetches all PENDING rows
            * Attempts to grade each one
        """

        logger.info("Starting Market Open Grader (interval: %ss)", self.check_interval)
        self.running = True

        while self.running:
            try:
                # Fetch all trades not yet resolved
                pending_sessions = MarketSession.objects.filter(wndw='PENDING')

                if pending_sessions.exists():
                    logger.debug("Grading %d pending sessions...", pending_sessions.count())

                    for session in pending_sessions:
                        self.grade_session(session)

                # Wait before next grading pass
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("Grading loop interrupted by user")
                self.running = False
                break

            except Exception as e:
                logger.error("Grading loop error: %s", e, exc_info=True)
                time.sleep(self.check_interval)

        logger.info("Market Open Grader stopped")

    def stop(self):
        """Stop the grading loop."""
        logger.info("Stopping Market Open Grader...")
        self.running = False


# ---------------------------------------------------------
# SINGLETON INSTANCE USED BY APP
# ---------------------------------------------------------
grader = MarketGrader()


def start_grading_service():
    """Start the grading service from CLI or background thread."""
    grader.run_grading_loop()


def stop_grading_service():
    """Stop the grading service."""
    grader.stop()


__all__ = ['start_grading_service', 'stop_grading_service', 'MarketGrader']
