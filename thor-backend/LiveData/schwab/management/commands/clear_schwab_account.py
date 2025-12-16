from decimal import Decimal
from typing import List

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ActAndPos.models import Account, Order, Position
from LiveData.schwab.models import BrokerConnection


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
        email = options["email"].strip()
        broker_account_id = (options.get("broker_account_id") or "").strip()
        display_name = (options.get("display_name") or "").strip()
        dry_run: bool = options["dry_run"]

        User = get_user_model()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist as exc:  # pragma: no cover - defensive guard
            raise CommandError(f"No user found with email {email}") from exc

        account_qs = Account.objects.filter(user=user, broker="SCHWAB")
        if broker_account_id:
            account_qs = account_qs.filter(broker_account_id__icontains=broker_account_id)
        if display_name:
            account_qs = account_qs.filter(display_name__icontains=display_name)

        account_ids: List[int] = list(account_qs.values_list("id", flat=True))

        connection_qs = BrokerConnection.objects.filter(
            user=user, broker=BrokerConnection.BROKER_SCHWAB
        )
        if broker_account_id:
            connection_qs = connection_qs.filter(broker_account_id__icontains=broker_account_id)

        positions_count = Position.objects.filter(account_id__in=account_ids).count()
        orders_count = Order.objects.filter(account_id__in=account_ids).count()
        accounts_count = account_qs.count()
        connections_count = connection_qs.count()

        if not any([positions_count, orders_count, accounts_count, connections_count]):
            self.stdout.write(
                self.style.WARNING(
                    "No Schwab account data found that matches the provided filters."
                )
            )
            return

        summary = (
            f"User: {user.email}\n"
            f"Accounts matched: {accounts_count}\n"
            f"Positions (unchanged): {positions_count}\n"
            f"Orders (unchanged): {orders_count}\n"
            f"Broker connections (unchanged): {connections_count}\n"
            f"Fields to reset: {', '.join(MONEY_FIELDS)}"
        )
        self.stdout.write(summary)

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete. No data was deleted."))
            return

        zero_payload = {field: Decimal("0") for field in MONEY_FIELDS}

        with transaction.atomic():
            updated_accounts = account_qs.update(**zero_payload)

        self.stdout.write(
            self.style.SUCCESS(
                f"Reset monetary fields for {updated_accounts} Schwab account(s)."
            )
        )
        self.stdout.write(
            "Positions, orders, and broker tokens remain untouched. Run again with --dry-run "
            "to preview matches."
        )
