#!/usr/bin/env python
"""Check if VwapMinute table exists in the database."""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from django.db import connection

print("Checking for VwapMinute table in database...\n")

with connection.cursor() as cursor:
    # Check if table exists
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE '%vwap%'
        ORDER BY table_name
    """)
    
    tables = cursor.fetchall()
    
    if tables:
        print(f"Found {len(tables)} VWAP-related table(s):")
        for table in tables:
            print(f"  - {table[0]}")
            
            # Show table structure
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table[0]}'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            print(f"    Columns ({len(columns)}):")
            for col in columns:
                print(f"      {col[0]} ({col[1]}, nullable={col[2]})")
    else:
        print("❌ No VWAP-related tables found in database")
        print("\nLet's check all FutureTrading tables:")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE 'FutureTrading_%'
            ORDER BY table_name
        """)
        ft_tables = cursor.fetchall()
        if ft_tables:
            print(f"\nFound {len(ft_tables)} FutureTrading tables:")
            for table in ft_tables:
                print(f"  - {table[0]}")
        else:
            print("No FutureTrading tables found")
