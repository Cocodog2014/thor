import csv

# Let's examine the actual CSV data more closely
csv_file = 'A:/Thor/CleanData-ComputerLearning.csv'

with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    
    print("=== CSV COLUMN ANALYSIS ===")
    print(f"Total columns: {len(reader.fieldnames)}")
    print("\nColumn names and sample values:")
    
    # Get first row to see actual data
    first_row = next(reader)
    
    # Check the key columns we're interested in
    key_columns = ['No._Trades', 'DLST', 'Year', 'Month', 'Date', 'OPEN', 'CLOSE', 'Volume', 
                   'WorldNetChange', 'WorldNetPercChange', 'WorldHigh', 'WorldLow']
    
    print("\n=== KEY FINANCIAL COLUMNS ===")
    for col in key_columns:
        value = first_row.get(col, 'NOT FOUND')
        print(f"{col:20}: '{value}'")
    
    print("\n=== ALL NON-EMPTY COLUMNS (first row) ===")
    non_empty = []
    for col, value in first_row.items():
        if value and value.strip():
            non_empty.append((col, value))
    
    print(f"Found {len(non_empty)} non-empty columns:")
    for i, (col, value) in enumerate(non_empty[:20], 1):  # Show first 20
        print(f"{i:2d}. {col:25}: '{value}'")
    
    if len(non_empty) > 20:
        print(f"... and {len(non_empty) - 20} more non-empty columns")
    
    print(f"\n=== SAMPLE OF ROWS 2-5 ===")
    f.seek(0)  # Reset file pointer
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= 5:
            break
        print(f"\nRow {i+1}:")
        print(f"  No._Trades: {row.get('No._Trades', 'N/A')}")
        print(f"  DLST: {row.get('DLST', 'N/A')}")
        print(f"  OPEN: {row.get('OPEN', 'N/A')}")
        print(f"  CLOSE: {row.get('CLOSE', 'N/A')}")
        print(f"  Volume: {row.get('Volume', 'N/A')}")