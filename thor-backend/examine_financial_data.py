#!/usr/bin/env python3

import pandas as pd

# Load the CSV
df = pd.read_csv('../CleanData-ComputerLearning.csv')

print("=== COMPREHENSIVE DATA ANALYSIS ===")
print(f"Total rows: {len(df)}")
print(f"Total columns: {len(df.columns)}")

print("\n=== DATE/TIME INFORMATION ===")
print("Date column sample:", df['Date'].iloc[:10].tolist())
print("Month column sample:", df['Month'].iloc[:10].tolist()) 
print("Day column sample:", df['Day'].iloc[:10].tolist())
print("Year column sample:", df['Year'].iloc[:10].tolist())

# Create actual date
print("\nActual dates (first 10 rows):")
for i in range(10):
    month_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    month_num = month_map.get(df['Month'].iloc[i], 1)
    date_str = f"{df['Year'].iloc[i]}-{month_num:02d}-{df['Date'].iloc[i]:02d}"
    print(f"Row {i}: {date_str}")

print("\n=== LOOKING FOR FINANCIAL COLUMNS ===")

# Check if there are columns with stock-like values
# Look for columns that might be prices - checking for decimal values in reasonable ranges
financial_candidates = []

for col in df.columns:
    if any(keyword in col.lower() for keyword in ['price', 'value', 'last', 'bid', 'ask', 'high', 'low', 'open', 'close']):
        try:
            # Get some sample values
            sample_values = df[col].dropna().iloc[:10].tolist()
            print(f"\n{col}: {sample_values}")
            
            # Try to convert to numeric and see if we get reasonable financial data
            numeric_series = pd.to_numeric(df[col], errors='coerce')
            if numeric_series.notna().sum() > 1000:
                # Check statistics
                valid_data = numeric_series.dropna()
                min_val = valid_data.min()
                max_val = valid_data.max()
                mean_val = valid_data.mean()
                
                # Financial data might be in reasonable ranges
                if 0.1 <= mean_val <= 50000:  # Reasonable price range
                    financial_candidates.append({
                        'column': col,
                        'min': min_val,
                        'max': max_val,
                        'mean': mean_val,
                        'count': len(valid_data)
                    })
        except:
            continue

print("\n=== POTENTIAL FINANCIAL COLUMNS ===")
for candidate in financial_candidates:
    print(f"{candidate['column']:30} | {candidate['count']:5} values | "
          f"${candidate['min']:8.2f} - ${candidate['max']:8.2f} | "
          f"avg: ${candidate['mean']:8.2f}")

print("\n=== CHECKING WORLD COLUMNS WITH NON-EMPTY DATA ===")
world_cols = [col for col in df.columns if 'world' in col.lower()]
for col in world_cols:
    non_empty = df[col].dropna()
    if len(non_empty) > 0:
        print(f"{col}: {non_empty.iloc[:5].tolist()}")

print("\n=== EXAMINING 'Last' COLUMN (MIGHT BE LAST PRICE) ===")
last_col = df['Last'].dropna()
print(f"Last column stats:")
print(f"  Count: {len(last_col)}")
print(f"  Min: ${last_col.min():.2f}")
print(f"  Max: ${last_col.max():.2f}")
print(f"  Mean: ${last_col.mean():.2f}")
print(f"  Sample values: {last_col.iloc[:10].tolist()}")

print("\n=== CHECKING BID/ASK DATA ===")
for col in ['Bid', 'Ask', 'BidSize', 'AskSize']:
    if col in df.columns:
        data = pd.to_numeric(df[col], errors='coerce').dropna()
        if len(data) > 0:
            print(f"{col}: count={len(data)}, min={data.min():.2f}, max={data.max():.2f}, mean={data.mean():.2f}")
            print(f"  Sample: {data.iloc[:5].tolist()}")