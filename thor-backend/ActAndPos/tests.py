from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from .models import Account
from .views.accounts import get_active_account
from .serializers import AccountSummarySerializer


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

	def test_defaults_to_schwab_when_available(self):
		# Create PAPER first to simulate the common "PAPER is id=1" scenario.
		Account.objects.create(
			user=self.user,
			broker="PAPER",
			broker_account_id="PAPER-001",
			display_name="Paper",
		)
		Account.objects.create(
			user=self.user,
			broker="SCHWAB",
			broker_account_id="SCH-001",
			display_name="Schwab",
		)

		request = self.factory.get("/actandpos/positions")
		request.user = self.user
		account = get_active_account(request)
		self.assertEqual(account.broker, "SCHWAB")


class DefaultPaperAccountSignalTests(TestCase):
	def test_signal_creates_paper_account_for_new_user(self):
		user = get_user_model().objects.create_user(
			email="signal-test@example.com",
			password="pass123",
		)

		accounts = Account.objects.filter(user=user, broker="PAPER")
		self.assertEqual(accounts.count(), 1)
		self.assertTrue(accounts.first().broker_account_id.startswith(f"PAPER-{user.id}-"))


class AccountSummarySerializerConnectionTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			email="summary@test.com",
			password="pass123",
		)

	def test_schwab_account_not_zeroed_with_live_connection(self):
		from LiveData.schwab.models import BrokerConnection

		# Create a non-expired token.
		import time

		BrokerConnection.objects.create(
			user=self.user,
			broker="SCHWAB",
			access_token="access",
			refresh_token="refresh",
			access_expires_at=int(time.time()) + 3600,
		)

		account = Account.objects.create(
			user=self.user,
			broker="SCHWAB",
			broker_account_id="SCH-ACCT-1",
			display_name="Schwab",
			net_liq=Decimal("123.00"),
			day_trading_buying_power=Decimal("1000.00"),
		)

		data = AccountSummarySerializer(account).data
		self.assertEqual(data["net_liq"], "123.00")
		self.assertTrue(data["ok_to_trade"])
