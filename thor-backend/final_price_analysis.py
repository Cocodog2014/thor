#!/usr/bin/env python3

import pandas as pd

# Load the CSV
df = pd.read_csv('../CleanData-ComputerLearning.csv')

print("=== ANALYZING 'Last' COLUMN (LIKELY LAST PRICE) ===")
last_col = df['Last']
print(f"Last column sample: {last_col.iloc[:10].tolist()}")

# Convert to numeric, treating errors as NaN
last_numeric = pd.to_numeric(last_col, errors='coerce')
last_valid = last_numeric.dropna()

print(f"Last column numeric stats:")
print(f"  Total entries: {len(last_col)}")
print(f"  Numeric entries: {len(last_valid)}")
print(f"  Non-numeric entries: {len(last_col) - len(last_valid)}")
print(f"  Min: ${last_valid.min():.2f}")
print(f"  Max: ${last_valid.max():.2f}")
print(f"  Mean: ${last_valid.mean():.2f}")

print("\n=== WORLD COLUMNS - ACTUAL STOCK PRICES ===")
world_price_cols = ['WorldOpen', 'WorldHigh', 'WorldLow', 'WorldClose']

for col in world_price_cols:
    if col in df.columns:
        # Convert to numeric
        col_data = pd.to_numeric(df[col], errors='coerce').dropna()
        if len(col_data) > 0:
            print(f"{col}:")
            print(f"  Count: {len(col_data)}")
            print(f"  Range: ${col_data.min():.2f} - ${col_data.max():.2f}")
            print(f"  Mean: ${col_data.mean():.2f}")
            print(f"  Sample: {col_data.iloc[:5].tolist()}")
            print()

print("=== CHECKING OPEN/HIGH/LOW/CLOSE NUMBER COLUMNS ===")
ohlc_number_cols = ['OpenNumber', 'HighNumber', 'LowValue', 'CloseValue']

for col in ohlc_number_cols:
    if col in df.columns:
        col_data = pd.to_numeric(df[col], errors='coerce').dropna()
        if len(col_data) > 0:
            print(f"{col}:")
            print(f"  Count: {len(col_data)}")
            print(f"  Range: ${col_data.min():.2f} - ${col_data.max():.2f}")
            print(f"  Mean: ${col_data.mean():.2f}")
            print(f"  Sample: {col_data.iloc[:5].tolist()}")
            print()

print("=== BID/ASK DATA ===")
for col in ['Bid', 'Ask']:
    if col in df.columns:
        col_data = pd.to_numeric(df[col], errors='coerce').dropna()
        if len(col_data) > 0:
            print(f"{col}:")
            print(f"  Count: {len(col_data)}")
            print(f"  Range: ${col_data.min():.2f} - ${col_data.max():.2f}")
            print(f"  Mean: ${col_data.mean():.2f}")
            print(f"  Sample: {col_data.iloc[:5].tolist()}")
            print()

print("=== CHECKING DATE DISTRIBUTION ===")
# Check what dates we have
date_summary = df.groupby(['Year', 'Month']).size().head(20)
print("Date distribution (first 20):")
print(date_summary)

print("\n=== CHECKING IF WE HAVE SYMBOL/TICKER DATA ===")
# Look for symbol columns
symbol_candidates = []
for col in df.columns:
    if any(word in col.lower() for word in ['symbol', 'ticker', 'stock', 'instrument', 'security']):
        symbol_candidates.append(col)

if symbol_candidates:
    print("Found potential symbol columns:")
    for col in symbol_candidates:
        sample_data = df[col].dropna().iloc[:10].tolist()
        print(f"  {col}: {sample_data}")
else:
    print("No obvious symbol/ticker columns found")
    
print("\n=== CONCLUSION ===")
print("Based on analysis, the best price columns appear to be:")
print("- WorldOpen: Opening prices")
print("- WorldHigh: High prices") 
print("- WorldLow: Low prices")
print("- WorldClose: Closing prices")
print("- Last: Last traded price (mixed data types)")
print("- Bid/Ask: Bid and Ask prices")
print("\nThe OPEN/CLOSE columns contain market hours (09:30:00/16:00:00), not prices")
print("The *Number and *Value columns may contain Excel serial dates or other encoded data")