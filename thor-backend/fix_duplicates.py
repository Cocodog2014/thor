#!/usr/bin/env python
"""Fix duplicate content types in the database"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.db import connection

# Raw SQL to find and remove duplicates
with connection.cursor() as cursor:
    # Find all duplicates
    cursor.execute("""
        SELECT app_label, model, COUNT(*) 
        FROM django_content_type 
        WHERE app_label = 'FutureTrading'
        GROUP BY app_label, model 
        HAVING COUNT(*) > 1
    """)
    
    duplicates = cursor.fetchall()
    
    if duplicates:
        print("Found duplicate content types:")
        for app, model, count in duplicates:
            print(f"  - {app}.{model}: {count} copies")
        
        # Delete ALL FutureTrading content types
        print("\nDeleting all FutureTrading content types...")
        cursor.execute("DELETE FROM django_content_type WHERE app_label = 'FutureTrading'")
        print(f"Deleted {cursor.rowcount} rows")
    else:
        print("No duplicates found")

print("\nNow run: python manage.py migrate")
