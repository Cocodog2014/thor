from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from .models import Account
from .views.accounts import get_active_account


class PaperAccountDefaultsTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			email="paper@test.com",
			password="pass123",
		)

	def test_paper_account_seeds_balances(self):
		account = Account.objects.create(
			user=self.user,
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
			user=self.user,
			broker="SCHWAB",
			broker_account_id="SCH-001",
			display_name="Real Account",
		)

		zero = Decimal("0")
		self.assertEqual(account.starting_balance, zero)
		self.assertEqual(account.current_cash, zero)
		self.assertEqual(account.equity, zero)


class GetActiveAccountTests(TestCase):
	def setUp(self):
		self.factory = APIRequestFactory()
		self.user = get_user_model().objects.create_user(
			email="captain@test.com",
			password="pass123",
		)

	def test_auto_creates_default_paper_account(self):
		request = self.factory.get("/actandpos/activity/today")
		request.user = self.user
		account = get_active_account(request)

		self.assertEqual(Account.objects.count(), 1)
		self.assertEqual(account.broker, "PAPER")
		expected_prefix = f"PAPER-{self.user.id}-"
		self.assertTrue(account.broker_account_id.startswith(expected_prefix))
		self.assertEqual(account.user, self.user)


class DefaultPaperAccountSignalTests(TestCase):
	def test_signal_creates_paper_account_for_new_user(self):
		user = get_user_model().objects.create_user(
			email="signal-test@example.com",
			password="pass123",
		)

		accounts = Account.objects.filter(user=user, broker="PAPER")
		self.assertEqual(accounts.count(), 1)
		self.assertTrue(accounts.first().broker_account_id.startswith(f"PAPER-{user.id}-"))
