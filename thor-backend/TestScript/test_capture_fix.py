"""Comprehensive Market Open capture verification script.

Enhanced from original target-only test:
  1. Displays sample enriched quotes & target calculations.
  2. Optionally purges existing MarketSession rows for today's date.
  3. Runs a market-open capture for a chosen country.
  4. Verifies per-future rows + TOTAL row counts and required fields.
  5. Summarizes any issues (missing futures, empty signals, etc.).

Environment overrides (optional):
  TEST_MARKET_COUNTRY=USA (default)
  PURGE_EXISTING=1 (purge today's rows before capture)

Exit code: 0 on success, 2 on verification issues, 1 on fatal error.
"""
import os
import sys
from decimal import Decimal
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thor_project.settings")
django.setup()

from django.utils import timezone
from FutureTrading.services.quotes import get_enriched_quotes_with_composite
from FutureTrading.services.TargetHighLow import compute_targets_for_symbol
from FutureTrading.views.MarketOpenCapture import capture_market_open
from FutureTrading.models.MarketSession import MarketSession
from GlobalMarkets.models import Market
from FutureTrading.constants import FUTURES_SYMBOLS

def show_sample_targets():
    print("\n=== SAMPLE ENRICHED QUOTES / TARGET LOGIC ===\n")
    enriched, composite = get_enriched_quotes_with_composite()
    print(f"Composite signal: {composite.get('composite_signal')}\n")
    for row in enriched[:5]:
        symbol = row['instrument']['symbol']
        ext = row.get('extended_data', {})
        individual_signal = (ext.get('signal') or '').upper()
        ask = row.get('ask')
        bid = row.get('bid')
        print(f"{symbol}: bhs={individual_signal}, ask={ask}, bid={bid}")
        if individual_signal and individual_signal not in ['HOLD', '']:
            if individual_signal in ['BUY', 'STRONG_BUY']:
                entry = Decimal(str(ask)) if ask else None
            elif individual_signal in ['SELL', 'STRONG_SELL']:
                entry = Decimal(str(bid)) if bid else None
            else:
                entry = None
            if entry:
                high, low = compute_targets_for_symbol(symbol, entry)
                print(f"  → entry={entry}, target_high={high}, target_low={low}")
            else:
                print("  → No entry price available")
        print()

def run_capture_and_verify(country: str) -> int:
    print("\n=== MARKET OPEN CAPTURE VERIFICATION ===\n")
    market = Market.objects.filter(country=country).first()
    if not market:
        print(f"❌ Market '{country}' not found.")
        return 1
    today = timezone.now().date()
    year, month, day = today.year, today.month, today.day

    if os.getenv('PURGE_EXISTING') == '1':
        deleted = MarketSession.objects.filter(country=country, year=year, month=month, date=day).count()
        MarketSession.objects.filter(country=country, year=year, month=month, date=day).delete()
        print(f"🧹 Purged existing {deleted} MarketSession rows for {country} {today}")

    print(f"Triggering capture for {country} ({today}) ...")
    session = capture_market_open(market)
    if not session:
        print("❌ Capture returned no session object.")
        return 1

    rows = MarketSession.objects.filter(country=country, year=year, month=month, date=day)
    total_row = rows.filter(future='TOTAL').first()
    futures_rows = rows.exclude(future='TOTAL').order_by('future')
    found_symbols = list(futures_rows.values_list('future', flat=True))

    print(f"\nCaptured rows: {rows.count()} (futures={len(found_symbols)}, TOTAL={'present' if total_row else 'missing'})")
    print(f"Futures found: {found_symbols}")

    expected_set = set(FUTURES_SYMBOLS)
    found_set = set(found_symbols)
    missing = sorted(expected_set - found_set)
    extras = sorted(found_set - expected_set)

    issues = []
    if missing:
        issues.append(f"Missing futures: {missing}")
    if extras:
        issues.append(f"Unexpected futures: {extras}")
    if not total_row:
        issues.append("TOTAL row missing")

    # Basic field validations per future
    for fr in futures_rows:
        missing_fields = []
        if fr.last_price is None:
            missing_fields.append('last_price')
        # Dollar Index (DX) may legitimately lack bid/ask from feed; treat as optional.
        if fr.future != 'DX':
            if (fr.bid_price is None) and (fr.ask_price is None):
                missing_fields.append('bid/ask')
        if fr.bhs in (None, ''):
            missing_fields.append('signal')
        if missing_fields:
            issues.append(f"{fr.future} missing {missing_fields}")

    if issues:
        print("\n⚠️  Verification issues:")
        for i in issues:
            print(f"  - {i}")
        return 2

    print("\n✅ Verification passed: all expected futures + TOTAL present with basic fields.")
    return 0


def main():
    country = os.getenv('TEST_MARKET_COUNTRY', 'USA')
    show_sample_targets()
    code = run_capture_and_verify(country)
    if code != 0:
        print(f"\nFinished with issues (exit code {code}).")
    else:
        print("\nAll checks passed successfully.")
    return code


if __name__ == '__main__':
    try:
        ec = main()
        sys.exit(ec)
    except Exception as e:
        print(f"\n💥 Fatal exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
