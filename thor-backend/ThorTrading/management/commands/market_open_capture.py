from django.core.management.base import BaseCommand

from ThorTrading.studies.futures_total.command_logic.market_open_capture import run


class Command(BaseCommand):
    help = "Run market open capture once for active markets (optionally filtered by country)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            dest="country",
            help="Only capture the specified country (case-insensitive match on Market.country)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            help="Force capture even if an OPEN capture already exists for the market-local date",
        )

    def handle(self, *args, **options):
        run(
            country=options.get("country"),
            force=bool(options.get("force")),
            stdout=self.stdout,
            style=self.style,
        )
