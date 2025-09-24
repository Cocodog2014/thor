import csv

# Check the first few rows to understand the data format
with open('A:/Thor/CleanData-ComputerLearning.csv', 'r') as f:
    reader = csv.DictReader(f)
    print("Column names:", list(reader.fieldnames))
    print("\nFirst 3 rows:")
    for i, row in enumerate(reader):
        if i >= 3:
            break
        print(f"\nRow {i+1}:")
        for key, value in list(row.items())[:10]:  # First 10 columns
            print(f"  {key}: {value}")