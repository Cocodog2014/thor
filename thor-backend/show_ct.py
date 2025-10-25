#!/usr/bin/env python
"""Show all content types for FutureTrading"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT id, app_label, model 
        FROM django_content_type 
        WHERE app_label = 'FutureTrading'
        ORDER BY model
    """)
    
    rows = cursor.fetchall()
    
    if rows:
        print(f"Found {len(rows)} FutureTrading content types:")
        for id, app, model in rows:
            print(f"  ID {id}: {app}.{model}")
        
        # Delete them all
        print("\nDeleting all...")
        cursor.execute("DELETE FROM django_content_type WHERE app_label = 'FutureTrading'")
        connection.commit()
        print(f"Deleted {cursor.rowcount} rows")
    else:
        print("No FutureTrading content types found")
