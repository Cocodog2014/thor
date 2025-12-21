import logging
import time

from django.core.management.base import BaseCommand


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Start Thor background supervisors (intraday, VWAP, Excel poller, etc.)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keepalive",
            type=int,
            default=30,
            help="Seconds to sleep between keepalive heartbeats (default: 30)",
        )

    def handle(self, *args, **options):
        keepalive = max(options.get("keepalive", 30), 1)

        from thor_project.realtime.runtime import start_realtime

        logger.info("🔥 run_thor_stack command launching Thor realtime stack...")
        start_realtime(force=True)
        self.stdout.write(self.style.SUCCESS("Thor realtime stack started."))

        try:
            while True:
                time.sleep(keepalive)
        except KeyboardInterrupt:
            logger.info("🛑 run_thor_stack command interrupted; exiting.")
            self.stdout.write(self.style.WARNING("Thor background stack stop requested."))
