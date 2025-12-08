from decimal import Decimal

from django.test import TestCase

from .models import Account


class PaperAccountDefaultsTests(TestCase):
	def test_paper_account_seeds_balances(self):
		account = Account.objects.create(
			broker="PAPER",
			broker_account_id="PAPER-001",
			display_name="Test Paper",
		)

		expected = Decimal("100000.00")
		self.assertEqual(account.starting_balance, expected)
		self.assertEqual(account.cash, expected)
		self.assertEqual(account.net_liq, expected)
		self.assertEqual(account.current_cash, expected)
		self.assertEqual(account.equity, expected)

	def test_real_account_does_not_override_balances(self):
		account = Account.objects.create(
			broker="SCHWAB",
			broker_account_id="SCH-001",
			display_name="Real Account",
		)

		zero = Decimal("0")
		self.assertEqual(account.starting_balance, zero)
		self.assertEqual(account.current_cash, zero)
		self.assertEqual(account.equity, zero)
