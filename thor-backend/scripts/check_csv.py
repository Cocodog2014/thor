import csv

with open('A:/Thor/CleanData-ComputerLearning.csv', 'r') as f:
    reader = csv.reader(f)
    header = next(reader)
    
# Count non-empty columns
named_columns = [col for col in header if col.strip()]
empty_columns = len(header) - len(named_columns)

print(f'Total columns: {len(header)}')
print(f'Named columns: {len(named_columns)}')
print(f'Empty columns: {empty_columns}')

print('\nFirst 20 named columns:')
for i, col in enumerate(named_columns[:20]):
    print(f'{i+1:2d}: {col}')

print('\nLast 10 named columns:')
for i, col in enumerate(named_columns[-10:], len(named_columns)-9):
    print(f'{i:2d}: {col}')

# Check if there are exactly 139 named columns
if len(named_columns) == 139:
    print(f'\n✅ Confirmed: {len(named_columns)} named columns as expected!')
else:
    print(f'\n⚠️  Expected 139 columns, found {len(named_columns)} named columns')