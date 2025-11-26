#!/usr/bin/env python
"""Find duplicate VwapMinute content types in database."""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from django.db import connection

print("Querying for all vwap-related content types...\n")

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT id, app_label, model
        FROM django_content_type
        WHERE model ILIKE %s
        ORDER BY id
    """, ['%vwap%'])
    
    rows = cursor.fetchall()
    
    if rows:
        print(f"Found {len(rows)} content type(s):")
        print("-" * 60)
        for row in rows:
            print(f"ID: {row[0]:4d} | app_label: {row[1]:20s} | model: {row[2]}")
        print("-" * 60)
        
        # Check for duplicates
        models_seen = {}
        duplicates = []
        for row in rows:
            key = (row[1], row[2])  # (app_label, model)
            if key in models_seen:
                duplicates.append((models_seen[key], row[0]))
                print(f"\n⚠️  DUPLICATE FOUND: {key}")
                print(f"    First:  ID {models_seen[key]}")
                print(f"    Second: ID {row[0]}")
            else:
                models_seen[key] = row[0]
        
        if not duplicates:
            print("\n✅ No duplicates found")
    else:
        print("No vwap-related content types found")
