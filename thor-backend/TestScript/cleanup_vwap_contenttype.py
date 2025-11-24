#!/usr/bin/env python
"""Cleanup duplicate VwapMinute content type.

Run once to fix migration error:
    python cleanup_vwap_contenttype.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
django.setup()

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from django.db import connection

print("Checking for VwapMinute content types...")

# First check how many exist
with connection.cursor() as cursor:
    cursor.execute(
        "SELECT id, app_label, model FROM django_content_type WHERE app_label = %s AND model = %s",
        ['FutureTrading', 'vwapminute']
    )
    rows = cursor.fetchall()
    print(f"Found {len(rows)} VwapMinute content type(s):")
    for row in rows:
        print(f"  ID: {row[0]}, app_label: {row[1]}, model: {row[2]}")

# Delete all related permissions first
with connection.cursor() as cursor:
    cursor.execute(
        """DELETE FROM auth_permission 
           WHERE content_type_id IN (
               SELECT id FROM django_content_type 
               WHERE app_label = %s AND model = %s
           )""",
        ['FutureTrading', 'vwapminute']
    )
    perm_deleted = cursor.rowcount
    print(f"Deleted {perm_deleted} permission(s)")

# Now delete ALL content types
with connection.cursor() as cursor:
    cursor.execute(
        "DELETE FROM django_content_type WHERE app_label = %s AND model = %s",
        ['FutureTrading', 'vwapminute']
    )
    deleted = cursor.rowcount
    print(f"✅ Force deleted {deleted} content type row(s) for VwapMinute")

# Verify deletion
with connection.cursor() as cursor:
    cursor.execute(
        "SELECT COUNT(*) FROM django_content_type WHERE app_label = %s AND model = %s",
        ['FutureTrading', 'vwapminute']
    )
    remaining = cursor.fetchone()[0]
    print(f"Remaining VwapMinute content types: {remaining}")

print("\nNow run: python manage.py migrate FutureTrading")
