from django.test import TestCase


class MetricsHelperTests(TestCase):
	def setUp(self):
		from ThorTrading.services.metrics import compute_row_metrics
		self.compute_row_metrics = compute_row_metrics

	def test_basic_metrics(self):
		row = {
			'price': '101.0',
			'open_price': '100.0',
			'previous_close': '99.0',
			'high_price': '105.0',
			'low_price': '95.0',
			'bid': '100.5',
			'ask': '101.5',
		}
		m = self.compute_row_metrics(row)
		self.assertAlmostEqual(m['last_prev_diff'], 2.0)
		self.assertAlmostEqual(m['last_prev_pct'], (2.0/99.0)*100)
		self.assertAlmostEqual(m['open_prev_diff'], 1.0)
		self.assertAlmostEqual(m['high_prev_diff'], 6.0)
		self.assertAlmostEqual(m['low_prev_diff'], -4.0)
		self.assertAlmostEqual(m['range_diff'], 10.0)
		self.assertAlmostEqual(m['spread'], 1.0)

	def test_handles_missing_and_zero_baseline(self):
		# Missing fields
		row = {
			'price': None,
			'open_price': '—',
			'previous_close': '0',
			'high_price': None,
			'low_price': None,
			'bid': None,
			'ask': None,
		}
		m = self.compute_row_metrics(row)
		# No numbers available → diffs None
		self.assertIsNone(m['last_prev_diff'])
		self.assertIsNone(m['open_prev_diff'])
		# prev_close = 0 → pct is None
		self.assertIsNone(m['last_prev_pct'])
		self.assertIsNone(m['open_prev_pct'])

# Create your tests here.

