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
import threading
from django.utils import timezone
from decimal import Decimal

from ThorTrading.models.vwap import VwapMinute
from ThorTrading.constants import FUTURES_SYMBOLS, REDIS_SYMBOL_MAP


def _dec(val):
    if val in (None, '', ' '):
        return None
    try:
        from decimal import Decimal as _D
        return _D(str(val))
    except Exception:
        return None


def _int(val):
    if val in (None, '', ' '):
        return None
    try:
        return int(val)
    except Exception:
        try:
            return int(float(val))
        except Exception:
            return None
from ThorTrading.models.MarketSession import MarketSession
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)

_GRADER_THREAD: threading.Thread | None = None
_GRADER_THREAD_LOCK = threading.Lock()
_CONTROL_MARKET_CACHE = {
    "timestamp": None,
    "is_open": True,
}


def _any_control_markets_open() -> bool:
    """Return True if any active control market is OPEN (cached for a few seconds)."""
    cache_t = _CONTROL_MARKET_CACHE["timestamp"]
    now = timezone.now()
    if cache_t and (now - cache_t).total_seconds() < 5:
        return _CONTROL_MARKET_CACHE["is_open"]

    try:
        from GlobalMarkets.models import Market

        is_open = Market.objects.filter(
            is_control_market=True,
            is_active=True,
            status="OPEN",
        ).exists()
    except Exception:
        logger.debug("GlobalMarkets availability check failed; assuming markets open.", exc_info=True)
        is_open = True

    _CONTROL_MARKET_CACHE["timestamp"] = now
    _CONTROL_MARKET_CACHE["is_open"] = is_open
    return is_open


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
        TOTAL → 'YM'   (system trade executed using YM quotes)
        DX    → '$DXY'  (your live feed provides DXY index, not DX futures)
        ALL OTHERS → use the symbol as-is (without leading slash).

        Returns:
            Decimal price or None if unavailable.
        """
        try:
            # Map special synthetic symbols to live Redis keys.
            if symbol == 'TOTAL':
                # TOTAL is graded using YM price (no slash)
                redis_key = 'YM'
            elif symbol == 'DX':
                # DX is graded using DXY index because DX futures aren't fed
                redis_key = '$DXY'
            else:
                # All other futures use their own symbol (strip leading slash if present)
                redis_key = symbol.lstrip('/')

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

        When WORKED / DIDNT_WORK is decided, we also record:
            - target_hit_at
            - target_hit_price
            - target_hit_type  ('TARGET' for profit target, 'STOP' for stop loss)

        Returns:
            True if the row is no longer PENDING (graded or neutral)
            False if still pending (unable to evaluate this cycle)
        """

        # Already graded → nothing to do
        if session.wndw != 'PENDING':
            return True

        # If no entry or missing targets → cannot grade → mark NEUTRAL
        if not session.entry_price or not session.target_high or not session.target_low:
            logger.debug(
                "⚠ %s (Session #%s) → NEUTRAL: missing entry=%s, target_h=%s, target_l=%s",
                session.future, session.session_number,
                session.entry_price, session.target_high, session.target_low
            )
            session.wndw = 'NEUTRAL'
            session.save(update_fields=['wndw'])
            return True

        # HOLD (or empty signal) → no trade → mark NEUTRAL
        if session.bhs in ['HOLD', None, '']:
            logger.debug(
                "⚠ %s (Session #%s) → NEUTRAL: signal=%s (no trade)",
                session.future, session.session_number, session.bhs
            )
            session.wndw = 'NEUTRAL'
            session.save(update_fields=['wndw'])
            return True

        # Get current price for exit evaluation
        current_price = self.get_current_price(session.future, session.bhs)
        if current_price is None:
            # Cannot grade without a live price
            logger.debug(
                "⏸ %s (Session #%s) → no price available yet (signal=%s)",
                session.future, session.session_number, session.bhs
            )
            return False

        worked = False
        didnt_work = False
        hit_type = None  # 'TARGET' or 'STOP'

        # LONG LOGIC (BUY / STRONG_BUY)
        if session.bhs in ['BUY', 'STRONG_BUY']:
            target = session.target_high    # profit target
            stop = session.target_low       # stop loss

            if current_price >= target:
                worked = True
                hit_type = 'TARGET'
            elif current_price <= stop:
                didnt_work = True
                hit_type = 'STOP'

        # SHORT LOGIC (SELL / STRONG_SELL)
        elif session.bhs in ['SELL', 'STRONG_SELL']:
            target = session.target_low     # profit target
            stop = session.target_high      # stop loss

            if current_price <= target:
                worked = True
                hit_type = 'TARGET'
            elif current_price >= stop:
                didnt_work = True
                hit_type = 'STOP'

        # Still inside the band → no decision this cycle
        if not worked and not didnt_work:
            return False

        # We have a decision: WORKED or DIDNT_WORK
        now = timezone.now()
        update_fields = ['wndw']

        # Only stamp the hit info the FIRST time this session is resolved
        if session.target_hit_at is None:
            session.target_hit_at = now
            session.target_hit_price = current_price
            session.target_hit_type = hit_type
            update_fields.extend(['target_hit_at', 'target_hit_price', 'target_hit_type'])

        if worked:
            session.wndw = 'WORKED'
            verb = "WORKED"
        else:
            session.wndw = 'DIDNT_WORK'
            verb = "DIDN'T WORK"

        session.save(update_fields=update_fields)

        logger.info(
            "✅ %s (Session #%s) %s at ~%s [hit_type=%s]",
            session.future,
            session.session_number,
            verb,
            current_price,
            hit_type,
        )
        return True



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

        # Track last persisted VWAP minute per symbol (avoid duplicates)
        last_minute_per_symbol = {}

        while self.running:
            try:
                if not _any_control_markets_open():
                    time.sleep(self.check_interval)
                    continue

                # Fetch all trades not yet resolved
                pending_sessions = MarketSession.objects.filter(wndw='PENDING')

                if pending_sessions.exists():
                    logger.debug("Grading %d pending sessions...", pending_sessions.count())

                    for session in pending_sessions:
                        self.grade_session(session)

                # --- VWAP Minute Snapshot (integrated) ---
                # Persist at minute boundary only; inexpensive check each loop.
                now = timezone.now()
                current_minute = now.replace(second=0, microsecond=0)
                for sym in FUTURES_SYMBOLS:
                    # Skip if already captured this minute for symbol
                    if last_minute_per_symbol.get(sym) == current_minute:
                        continue
                    redis_key = REDIS_SYMBOL_MAP.get(sym, sym)
                    quote = live_data_redis.get_latest_quote(redis_key)
                    if not quote:
                        continue
                    # Create or ignore duplicate (race protection if loop overlaps minute change)
                    try:
                        VwapMinute.objects.get_or_create(
                            symbol=sym,
                            timestamp_minute=current_minute,
                            defaults={
                                'last_price': _dec(quote.get('last')),
                                'cumulative_volume': _int(quote.get('volume')),
                            }
                        )
                        last_minute_per_symbol[sym] = current_minute
                    except Exception as vw_err:
                        logger.debug("VWAP minute capture failed for %s: %s", sym, vw_err)

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


def start_grading_service(*, blocking: bool = False) -> bool:
    """Start the grading service.

    Args:
        blocking: When True, run synchronously (used by management commands).
    Returns:
        bool indicating whether a new loop was started.
    """

    if blocking:
        logger.info("MarketGrader starting in blocking mode.")
        grader.run_grading_loop()
        return True

    global _GRADER_THREAD
    with _GRADER_THREAD_LOCK:
        if _GRADER_THREAD and _GRADER_THREAD.is_alive():
            logger.info("MarketGrader already running; skip new start.")
            return False

        thread = threading.Thread(
            target=grader.run_grading_loop,
            name="MarketGraderLoop",
            daemon=True,
        )
        thread.start()
        _GRADER_THREAD = thread
        logger.info("MarketGrader background thread started.")
        return True


def stop_grading_service(*, wait: bool = False):
    """Stop the grading service (optionally waiting for the loop to exit)."""

    global _GRADER_THREAD
    grader.stop()
    if not wait:
        return

    thread = _GRADER_THREAD
    if thread and thread.is_alive():
        thread.join(timeout=10)

    if thread and not thread.is_alive():
        with _GRADER_THREAD_LOCK:
            if _GRADER_THREAD is thread:
                _GRADER_THREAD = None



__all__ = ['start_grading_service', 'stop_grading_service', 'MarketGrader']

