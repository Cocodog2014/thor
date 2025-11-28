# Precision-Agnostic Target Computation

## Overview
Target high/low computation now respects per-symbol decimal precision configured in the admin dashboard, eliminating all hard-coded precision values from the codebase.

## Architecture

### 1. Model Layer (`TargetHighLowConfig`)
- `compute_targets(entry_price, quant=None)` accepts optional quantization unit
- No hard-coded `0.01` or precision assumptions
- Pure math: caller provides quantization or gets unrounded result

### 2. Service Layer (`targets.py`)
- `_get_quant_for_symbol(symbol)` queries `TradingInstrument.display_precision`
- Builds quantization unit: `precision=2 → Decimal('0.01')`, `precision=3 → Decimal('0.001')`
- `compute_targets_for_symbol()` orchestrates lookup + computation

### 3. Admin Configuration
- **TradingInstrument.display_precision** controls all decimal behavior
- Examples:
  - YM (Dow): `display_precision=0` → whole numbers
  - ES (S&P): `display_precision=2` → 0.01
  - SI (Silver): `display_precision=3` → 0.001
  - HG (Copper): `display_precision=4` → 0.0001

## Usage

### Setting Precision (Admin Dashboard)
```python
# In Django Admin → Trading Instruments
YM: display_precision = 0  # 43500, 43700
ES: display_precision = 2  # 4500.00, 4525.00
SI: display_precision = 3  # 24.125, 24.625
HG: display_precision = 4  # 4.2500, 4.2750
```

### Code Usage (Already Implemented)
```python
from FutureTrading.services.TargetHighLow import compute_targets_for_symbol

entry = Decimal('4500.00')
high, low = compute_targets_for_symbol('ES', entry)
# Returns values respecting ES's display_precision setting
```

## Benefits

1. **No Hard-Coded Precision**: All decimal places controlled via admin UI
2. **Symbol-Specific Behavior**: Each instrument uses its natural precision
3. **Future-Proof**: Adding new instruments with different precision requires only DB config
4. **Centralized Control**: Single source of truth in `TradingInstrument.display_precision`

## Migration Notes

- DB schema already has sufficient precision (`decimal_places=2` in storage is fine)
- Display precision (0/1/2/3/4) controlled by admin config
- Legacy fallback (±20) also respects precision when TradingInstrument exists
- Missing instruments: targets computed without quantization (logs warning)

## Testing

Run precision tests:
```bash
python manage.py test FutureTrading.tests.test_precision_targets
```

Tests verify:
- 0/2/3 decimal precision handling
- Point and percent modes
- Legacy fallback behavior
- Missing instrument edge cases
