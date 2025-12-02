"""Verify MarketOpenCapture across all control markets.

Workflow:
  1. Optionally purge today's MarketSession rows per market (PURGE_EXISTING_ALL=1).
  2. Iterate through control countries (ThorTrading.constants.CONTROL_COUNTRIES) OR all active markets.
  3. Invoke capture_market_open(market) for each (ignores market.status — intended for diagnostic run).
  4. Validate per-future rows (expected FUTURES_SYMBOLS) + TOTAL row.
  5. Print summary table and exit code 0 if all pass; 2 if any market has issues; 1 on fatal error.

Environment variables:
  USE_ACTIVE_MARKETS=1     -> Use GlobalMarkets.models.Market filter(is_active=True) instead of CONTROL_COUNTRIES
  PURGE_EXISTING_ALL=1     -> Purge existing rows for today before each capture
  STRICT_STATUS=1          -> Only run capture if market.status == 'OPEN' (default: ignore)
  DRY_RUN=1                -> Do not call capture; only report existing rows

Notes:
  - capture_market_open checks enable_futures_capture & enable_open_capture but not status.
  - Running for closed markets will still create a snapshot using current quotes.
"""
import os
import sys
import django
from typing import List, Dict

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thor_project.settings")

try:
    django.setup()
except Exception as e:
    print(f"Failed Django setup: {e}")
    sys.exit(1)

from django.utils import timezone
from ThorTrading.constants import FUTURES_SYMBOLS, CONTROL_COUNTRIES
from GlobalMarkets.models import Market
from ThorTrading.views.MarketOpenCapture import capture_market_open
from ThorTrading.models.MarketSession import MarketSession

TODAY = timezone.now().date()
YEAR, MONTH, DAY = TODAY.year, TODAY.month, TODAY.day  # Server local date (used only for purge)

USE_ACTIVE = os.getenv('USE_ACTIVE_MARKETS') == '1'
PURGE = os.getenv('PURGE_EXISTING_ALL') == '1'
STRICT_STATUS = os.getenv('STRICT_STATUS') == '1'
DRY_RUN = os.getenv('DRY_RUN') == '1'

EXPECTED_SET = set(FUTURES_SYMBOLS)

header = f"\n=== VERIFY MARKET OPEN CAPTURE FOR {TODAY} ===\n"
print(header)
print(f"Options: USE_ACTIVE={USE_ACTIVE} PURGE={PURGE} STRICT_STATUS={STRICT_STATUS} DRY_RUN={DRY_RUN}\n")

if USE_ACTIVE:
    markets_qs = Market.objects.filter(is_active=True)
    markets: List[Market] = list(markets_qs)
    # Order by country name for consistency
    markets.sort(key=lambda m: m.country)
else:
    # Map control countries to actual market objects if present
    markets: List[Market] = []
    for c in CONTROL_COUNTRIES:
        m = Market.objects.filter(country=c).first()
        if m:
            markets.append(m)

if not markets:
    print("No markets found to process.")
    sys.exit(1)

results: Dict[str, Dict] = {}

session_numbers = {}

for market in markets:
    country = market.country
    print(f"\n--- {country} ---")
    # Skip if capture disabled at market level
    if not getattr(market, 'enable_futures_capture', True) or not getattr(market, 'enable_open_capture', True):
        reason_parts = []
        if not getattr(market, 'enable_futures_capture', True):
            reason_parts.append('futures_capture_disabled')
        if not getattr(market, 'enable_open_capture', True):
            reason_parts.append('open_capture_disabled')
        reason = ','.join(reason_parts) or 'capture_disabled'
        print(f"Skipping (disabled flags: {reason})")
        results[country] = {"skipped": True, "reason": reason}
        continue
    if STRICT_STATUS and market.status != 'OPEN':
        print(f"Skipping (status={market.status}) due to STRICT_STATUS.")
        results[country] = {"skipped": True, "reason": f"status={market.status}"}
        continue

    if PURGE:
        # Purge ANY rows for today (server date) OR last 2 probable local dates to handle timezone lead (e.g., Asia already next day)
        pre_ct = MarketSession.objects.filter(country=country, year__in=[YEAR, YEAR], month=MONTH, date__in=[DAY, DAY+1 if DAY < 31 else DAY]).count()
        MarketSession.objects.filter(country=country, year__in=[YEAR, YEAR], month=MONTH, date__in=[DAY, DAY+1 if DAY < 31 else DAY]).delete()
        print(f"Purged {pre_ct} existing rows for {country}.")

    if DRY_RUN:
        existing = MarketSession.objects.filter(country=country, year=YEAR, month=MONTH, date=DAY)
        total_row = existing.filter(future='TOTAL').first()
        futures_found = list(existing.exclude(future='TOTAL').values_list('future', flat=True))
        results[country] = {
            "performed": False,
            "count": existing.count(),
            "futures": futures_found,
            "missing": sorted(EXPECTED_SET - set(futures_found)),
            "has_total": total_row is not None,
        }
        print(f"DRY-RUN existing rows={existing.count()} futures={len(futures_found)} TOTAL={'yes' if total_row else 'no'}")
        continue

    # Perform capture
    try:
        session = capture_market_open(market)
    except Exception as e:
        print(f"❌ Capture exception: {e}")
        results[country] = {"performed": True, "error": str(e)}
        continue

    if not session:
        # If capture returned None but market still enabled treat as error.
        print("❌ Capture returned no session object")
        results[country] = {"performed": True, "error": "no session"}
        continue

    # Store session number for optional later correlation
    session_numbers[country] = session.session_number
    # Query rows by session_number (robust to local date differences/timezones)
    rows = MarketSession.objects.filter(country=country, session_number=session.session_number)
    total_row = rows.filter(future='TOTAL').first()
    futures_rows = rows.exclude(future='TOTAL').order_by('future')
    futures_found = list(futures_rows.values_list('future', flat=True))

    missing = sorted(EXPECTED_SET - set(futures_found))
    extras = sorted(set(futures_found) - EXPECTED_SET)
    issues = []
    if missing:
        issues.append(f"missing futures: {missing}")
    if extras:
        issues.append(f"unexpected futures: {extras}")
    if not total_row:
        issues.append("TOTAL row missing")

    # Basic field check for each future
    for fr in futures_rows:
        mf = []
        if fr.last_price is None:
            mf.append('last_price')
        if fr.future != 'DX':
            if (fr.bid_price is None) and (fr.ask_price is None):
                mf.append('bid/ask')
        if fr.bhs in (None, ''):
            mf.append('signal')
        if mf:
            issues.append(f"{fr.future} missing {mf}")

    results[country] = {
        "performed": True,
        "count": rows.count(),
        "futures": futures_found,
        "has_total": total_row is not None,
        "issues": issues,
    }

    if issues:
       print(f"⚠️ Issues: {issues}")
    else:
       print(f"✅ OK: {len(futures_found)} futures + TOTAL (count={rows.count()})")

# Summary
print("\n=== SUMMARY ===")
all_ok = True
for country, info in results.items():
    if info.get("skipped"):
        print(f"{country}: SKIPPED ({info['reason']})")
        continue
    if info.get("error"):
        print(f"{country}: ERROR {info['error']}")
        all_ok = False
        continue
    issues = info.get('issues', [])
    if issues:
        print(f"{country}: {len(info.get('futures', []))} futures, TOTAL={'yes' if info.get('has_total') else 'no'} → Issues: {issues}")
        all_ok = False
    else:
        print(f"{country}: OK ({len(info.get('futures', []))} futures + TOTAL)")

exit_code = 0 if all_ok else 2
print(f"\nExit code: {exit_code}")
sys.exit(exit_code)

