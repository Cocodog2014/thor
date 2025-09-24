import csv

# Let's find columns that might contain actual price data
csv_file = 'A:/Thor/CleanData-ComputerLearning.csv'

with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    first_row = next(reader)
    
    print("=== LOOKING FOR PRICE-LIKE DATA ===")
    print("Searching for columns with numeric decimal values that could be prices...")
    
    potential_price_columns = []
    
    for col, value in first_row.items():
        if value and value.strip():
            # Look for decimal numbers that could be prices
            try:
                float_val = float(value)
                # Price-like: positive numbers, possibly with decimals
                if float_val > 0 and '.' in value:
                    potential_price_columns.append((col, value, float_val))
            except ValueError:
                continue
    
    print(f"\nFound {len(potential_price_columns)} columns with price-like values:")
    for i, (col, value, float_val) in enumerate(potential_price_columns[:20], 1):
        print(f"{i:2d}. {col:30}: {value:>15} ({float_val:,.2f})")
    
    print("\n=== CHECKING COLUMNS WITH 'PRICE', 'OPEN', 'CLOSE', 'HIGH', 'LOW' ===")
    price_keywords = ['price', 'open', 'close', 'high', 'low', 'value', 'number']
    
    matching_cols = []
    for col in first_row.keys():
        col_lower = col.lower()
        for keyword in price_keywords:
            if keyword in col_lower:
                value = first_row.get(col, '')
                matching_cols.append((col, value))
                break
    
    for col, value in matching_cols:
        print(f"{col:35}: '{value}'")
    
    print("\n=== EXAMINING COLUMNS WITH 'World' (might be price data) ===")
    world_cols = [col for col in first_row.keys() if 'World' in col or 'world' in col]
    for col in world_cols:
        value = first_row.get(col, '')
        print(f"{col:35}: '{value}'")
    
    print("\n=== CHECKING LAST 20 NON-EMPTY COLUMNS ===")
    non_empty = [(col, value) for col, value in first_row.items() if value and value.strip()]
    print("Last 20 columns with data:")
    for col, value in non_empty[-20:]:
        print(f"{col:35}: '{value}'")