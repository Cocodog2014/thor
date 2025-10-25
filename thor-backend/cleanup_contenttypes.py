#!/usr/bin/env python
"""Clean up duplicate content types for FutureTrading app"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.contenttypes.models import ContentType

# Get all FutureTrading content types
all_cts = ContentType.objects.filter(app_label='FutureTrading').order_by('model')

print("Current FutureTrading content types in database:")
for ct in all_cts:
    print(f"  - {ct.model}")

print("\nDeleting all FutureTrading content types to force refresh...")
count = ContentType.objects.filter(app_label='FutureTrading').delete()
print(f"Deleted {count[0]} objects: {count[1]}")

print("\nNow run: python manage.py migrate")
