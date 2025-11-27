# FutureTrading/services/stack_start.py
import logging

logger = logging.getLogger(__name__)


def start_thor_background_stack():
    """
    Master start function for all Thor background supervisors.
    For now, it's empty. We will add supervisors step-by-step.
    """
    logger.info("🚀 Thor background stack start called (currently empty).")


def stop_thor_background_stack():
    """
    Master stop function for all Thor background supervisors.
    Also empty for now. We will fill it in later.
    """
    logger.info("🛑 Thor background stack stop called (currently empty).")
