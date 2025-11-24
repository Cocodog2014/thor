import os
import sys
import django

# Ensure project root on path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(ROOT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from django.db import connection

print("Executing column reordering script...")
with open('scripts/reorder_marketsession_columns.sql', 'r') as f:
    sql = f.read()

try:
    with connection.cursor() as cursor:
        cursor.execute(sql)
    print("✓ Column reordering complete!")
    
    # Verify
    cursor = connection.cursor()
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'FutureTrading_marketsession' 
        ORDER BY ordinal_position
    """)
    cols = [row[0] for row in cursor.fetchall()]
    
    # Check target_hit columns are after entry_price
    entry_idx = cols.index('entry_price')
    target_hit_price_idx = cols.index('target_hit_price')
    target_hit_at_idx = cols.index('target_hit_at')
    target_hit_type_idx = cols.index('target_hit_type')
    
    print(f"\nColumn positions:")
    print(f"  entry_price: {entry_idx + 1}")
    print(f"  target_hit_price: {target_hit_price_idx + 1}")
    print(f"  target_hit_at: {target_hit_at_idx + 1}")
    print(f"  target_hit_type: {target_hit_type_idx + 1}")
    
    if target_hit_price_idx == entry_idx + 1 and target_hit_at_idx == entry_idx + 2:
        print("\n✓ Columns successfully reordered!")
    else:
        print("\n⚠ Warning: Columns may not be in expected order")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
