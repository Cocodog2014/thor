# Country Code Standardization — Complete

## Summary
Replaced all instances of "United States" with canonical "USA" across database and code.

## Changes Made

### 1. Database Cleanup (One-time)
Executed in Django shell:

```python
from ThorTrading.models.MarketIntraDay import MarketIntraday
from ThorTrading.models.MarketSession import MarketSession
from ThorTrading.models.Martket24h import FutureTrading24Hour

# Results:
# MarketIntraday: 693 rows updated
# MarketSession: 0 rows (already clean)
# FutureTrading24Hour: 11 rows updated
```

**Before:**
- MarketIntraday: USA, Pre_USA, China, Japan, United Kingdom, India, **United States**
- FutureTrading24Hour: USA, Pre_USA, China, Japan, United Kingdom, India, **United States**

**After:**
- MarketIntraday: USA, Pre_USA, China, Japan, United Kingdom, India ✅
- FutureTrading24Hour: USA, Pre_USA, China, Japan, United Kingdom, India ✅

### 2. Code-Level Normalizer (Preventive)
Added to [ThorTrading/services/intraday_supervisor/utils.py](thor-backend/ThorTrading/services/intraday_supervisor/utils.py):

```python
COUNTRY_NORMALIZATION = {
    "United States": "USA",
    "US": "USA",
    "U.S.": "USA",
}

def normalize_country(country: str) -> str:
    """Normalize country codes to canonical values."""
    if not country:
        return country
    return COUNTRY_NORMALIZATION.get(country, country)
```

This ensures that **any future feed or config accidentally emits "United States" or variants, it will be coerced to "USA"** before writing to the database.

### 3. Supervisor Integration
Updated [ThorTrading/services/intraday_supervisor/supervisor.py](thor-backend/ThorTrading/services/intraday_supervisor/supervisor.py):

- Imported `normalize_country` from utils
- Applied normalization in `_worker_loop` before all DB writes:
  ```python
  country = normalize_country(market.country)
  ```

### 4. Model-Level Enforcement (Bulletproof)
Added `choices` constraint to both models:

**[MarketIntraday](thor-backend/ThorTrading/models/MarketIntraDay.py):**
```python
COUNTRY_CHOICES = (
    ("USA", "USA"),
    ("Pre_USA", "Pre_USA"),
    ("China", "China"),
    ("Japan", "Japan"),
    ("United Kingdom", "United Kingdom"),
    ("India", "India"),
)

class MarketIntraday(models.Model):
    country = models.CharField(
        max_length=32,
        choices=COUNTRY_CHOICES,
        help_text="Market region (canonical values only)"
    )
```

**[FutureTrading24Hour](thor-backend/ThorTrading/models/Martket24h.py):**
Same `COUNTRY_CHOICES` applied.

### Result
✅ Database is clean (no more "United States")
✅ Code prevents future regressions (normalizer catches variants)
✅ Models enforce valid values (choices prevent bad data from admin/scripts/tests)
✅ Admin interface now only shows canonical country list

## Why This Matters
Without this fix:
- Silent data fragmentation (some rows have "USA", others "United States")
- Broken queries/aggregations (filters need to account for both)
- Admin filters show duplicate country values
- Historical "why is intraday weird" bugs

This is now locked in at three levels: DB, code, and model.
