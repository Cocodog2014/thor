#!/usr/bin/env python3

import pandas as pd
from datetime import datetime, timedelta

# Load the CSV
df = pd.read_csv('../CleanData-ComputerLearning.csv')

print("=== ANALYZING POTENTIAL EXCEL DATE COLUMNS ===")

# Check if these numbers are Excel serial dates
# Excel serial date 43427 should be around 2019
test_values = [43427, 43429, 43457, 43459]

print("Converting potential Excel serial dates:")
for val in test_values:
    try:
        # Excel epoch starts at 1900-01-01, but has a leap year bug
        # Python datetime: 1900-01-01 is day 1, but Excel considers 1900-01-01 as day 1
        excel_date = datetime(1899, 12, 30) + timedelta(days=val)
        print(f"  {val} -> {excel_date.strftime('%Y-%m-%d')}")
    except:
        print(f"  {val} -> Invalid date")

print("\n=== CHECKING FOR ACTUAL PRICE DATA ===")

# Look for columns that might contain actual financial data
# Check columns that have consistent numeric values across multiple rows
numeric_columns = []
for col in df.columns:
    try:
        # Try to convert column to numeric
        numeric_series = pd.to_numeric(df[col], errors='coerce')
        non_null_count = numeric_series.notna().sum()
        
        if non_null_count > 1000:  # Has substantial data
            # Check if values are in reasonable price ranges (0.01 to 10000)
            valid_prices = numeric_series[(numeric_series > 0.01) & (numeric_series < 10000)]
            if len(valid_prices) > 100:
                mean_val = valid_prices.mean()
                min_val = valid_prices.min()
                max_val = valid_prices.max()
                numeric_columns.append((col, len(valid_prices), min_val, mean_val, max_val))
    except:
        continue

# Sort by number of valid values
numeric_columns.sort(key=lambda x: x[1], reverse=True)

print("Columns with potential price data (0.01-10000 range):")
for col, count, min_val, mean_val, max_val in numeric_columns[:20]:
    print(f"  {col:30} | {count:5} values | ${min_val:8.2f} - ${max_val:8.2f} | avg: ${mean_val:8.2f}")

print("\n=== EXAMINING FIRST FEW ROWS OF POTENTIAL PRICE COLUMNS ===")
if numeric_columns:
    # Show first few rows of top candidates
    top_candidates = [col[0] for col in numeric_columns[:5]]
    print("First 5 rows of top price candidates:")
    for col in top_candidates:
        print(f"\n{col}:")
        values = pd.to_numeric(df[col], errors='coerce').dropna().head()
        for i, val in enumerate(values):
            print(f"  Row {i}: ${val:.2f}")

print("\n=== LOOKING FOR TICKER SYMBOL OR DATE COLUMNS ===")
# Look for identifying information
for col in ['Symbol', 'Ticker', 'Date', 'TIME', 'MONTH', 'DAY', 'YEAR']:
    if col in df.columns:
        print(f"{col}: {df[col].iloc[0:5].tolist()}")
    elif col.lower() in [c.lower() for c in df.columns]:
        # Case insensitive search
        actual_col = next(c for c in df.columns if c.lower() == col.lower())
        print(f"{actual_col}: {df[actual_col].iloc[0:5].tolist()}")