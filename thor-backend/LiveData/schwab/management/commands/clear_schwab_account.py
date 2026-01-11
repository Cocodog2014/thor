from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from LiveData.schwab.models import BrokerConnection

# Legacy command stub - ActAndPos.models no longer exist
# Now operates on BrokerConnection + Live/Paper balance models


MONEY_FIELDS = [
    "net_liq",
    "cash",
    "starting_balance",
    "current_cash",
    "equity",
    "stock_buying_power",
    "option_buying_power",
    "day_trading_buying_power",
]


class Command(BaseCommand):
    help = "Reset Schwab account financial values without deleting the account."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            required=True,
            help="Email address of the Thor user who owns the Schwab connection.",
        )
        parser.add_argument(
            "--broker-account-id",
            help="Exact or partial broker account identifier (e.g. 0485).",
        )
        parser.add_argument(
            "--display-name",
            help="Case-insensitive match on the trading account display name.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without touching the database.",
        )

    def handle(self, *_, **options):
        raise CommandError(
            "This command is disabled after ActAndPos.models removal. "
            "TODO: Reimplement using LiveBalance/PaperBalance models."
        )
