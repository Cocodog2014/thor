#!/usr/bin/env python
"""Manually create content types for FutureTrading models"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.contenttypes.models import ContentType
from django.apps import apps

# Get the FutureTrading app config
app_config = apps.get_app_config('FutureTrading')

print(f"Models in FutureTrading app:")
for model in app_config.get_models():
    print(f"  - {model._meta.model_name}")
    
    # Try to get or create content type
    ct, created = ContentType.objects.get_or_create(
        app_label='FutureTrading',
        model=model._meta.model_name,
        defaults={'app_label': 'FutureTrading', 'model': model._meta.model_name}
    )
    
    if created:
        print(f"    ✓ Created content type")
    else:
        print(f"    ✓ Already exists (ID: {ct.id})")

print("\nDone! Now try: python manage.py runserver")
