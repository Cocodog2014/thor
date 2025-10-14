from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from account_statement.models.paper import PaperAccount
from decimal import Decimal


class Command(BaseCommand):
    help = 'Seed a PaperAccount with $10,000 for an existing user (admin@360edu.org preferred).'

    def handle(self, *args, **options):
        User = get_user_model()

        user = None
        # Prefer known admin email if exists
        try:
            user = User.objects.filter(email__iexact='admin@360edu.org').first()
        except Exception:
            user = None

        if not user:
            user = User.objects.first()

        if not user:
            self.stdout.write(self.style.ERROR('No users found. Create a user first, then re-run.'))
            return

        acct, created = PaperAccount.objects.get_or_create(user=user, defaults={
            'starting_balance': Decimal('10000.00'),
        })

        if created:
            # Ensure balances reflect starting balance
            acct.current_balance = Decimal('10000.00')
            acct.net_liquidating_value = Decimal('10000.00')
            acct.stock_buying_power = Decimal('10000.00')
            acct.option_buying_power = Decimal('10000.00')
            acct.available_funds_for_trading = Decimal('10000.00')
            acct.equity_percentage = Decimal('100.00')
            acct.save()
            self.stdout.write(self.style.SUCCESS(f'Created PaperAccount for {user.email} with $10,000.'))
        else:
            self.stdout.write(self.style.WARNING(f'PaperAccount already exists for {user.email}. No changes made.'))
