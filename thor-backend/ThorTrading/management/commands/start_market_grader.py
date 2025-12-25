from __future__ import annotations
"""
Start the Market Open Grader loop.

Usage:
    python manage.py start_market_grader

This runs an infinite loop that:
- Looks for MarketSession rows with wndw='PENDING'
- Uses live quotes from Redis
- Updates wndw to WORKED / DIDNT_WORK / NEUTRAL

Stop it with Ctrl+C in the terminal.
"""

import logging
from django.core.management.base import BaseCommand

from ThorTrading.api.views.market_grader import start_grading_service, stop_grading_service


def _heartbeat_active() -> bool:
    return os.getenv("THOR_SCHEDULER_MODE", "heartbeat").lower() == "heartbeat"

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Start the Market Open Grader background loop"

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=float,
            default=0.5,
            help='Seconds between grading checks (default: 0.5)',
        )

    def handle(self, *args, **options):
        interval = options['interval']

        if _heartbeat_active():
            msg = "Heartbeat scheduler is active; start_market_grader is obsolete. Use heartbeat jobs instead."
            logger.warning(msg)
            self.stdout.write(self.style.WARNING(msg))
            return

        # Optional: log the configured interval
        logger.info("Starting MarketGrader with interval=%ss", interval)
        self.stdout.write(self.style.SUCCESS(
            f"Starting MarketGrader (interval={interval}s). Press Ctrl+C to stop."
        ))

            # NOTE:
            # Our MarketGrader currently gets its interval in __init__.
            # If you want to use the CLI interval, you can modify MarketGrader
        # to accept it or just leave it at the default.
        try:
            start_grading_service(blocking=True)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("MarketGrader interrupted by user (Ctrl+C)."))
        except Exception as e:
            logger.exception("MarketGrader crashed: %s", e)
            self.stderr.write(self.style.ERROR(f"MarketGrader error: {e}"))
        finally:
            try:
                stop_grading_service(wait=True)
            except Exception:
                logger.exception("Error while stopping MarketGrader")
            self.stdout.write(self.style.SUCCESS("MarketGrader stopped."))

