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

cursor = connection.cursor()
cursor.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'FutureTrading_marketsession' 
    ORDER BY ordinal_position
""")

cols = [row[0] for row in cursor.fetchall()]
print("Current columns in table:")
for i, col in enumerate(cols, 1):
    print(f"{i:3}. {col}")
