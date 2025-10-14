from django.core.management.base import BaseCommand
from account_statement.models.paper import PaperAccount
from decimal import Decimal


class Command(BaseCommand):
    help = 'Reset ALL PaperAccounts to a $10,000 starting balance and align balances accordingly.'

    def handle(self, *args, **options):
        count = 0
        for acct in PaperAccount.objects.all():
            acct.starting_balance = Decimal('10000.00')
            acct.current_balance = Decimal('10000.00')
            acct.net_liquidating_value = Decimal('10000.00')
            acct.stock_buying_power = Decimal('10000.00')
            acct.option_buying_power = Decimal('10000.00')
            acct.available_funds_for_trading = Decimal('10000.00')
            acct.equity_percentage = Decimal('100.00')
            acct.long_stock_value = Decimal('0.00')
            acct.save()
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Reset {count} paper account(s) to $10,000.'))
