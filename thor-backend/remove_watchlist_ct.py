#!/usr/bin/env python
"""Remove obsolete WatchlistGroup and WatchlistItem content types"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.contenttypes.models import ContentType

# Delete WatchlistGroup content type
deleted1 = ContentType.objects.filter(app_label='FutureTrading', model='watchlistgroup').delete()
print(f"Deleted WatchlistGroup content type: {deleted1}")

# Delete WatchlistItem content type
deleted2 = ContentType.objects.filter(app_label='FutureTrading', model='watchlistitem').delete()
print(f"Deleted WatchlistItem content type: {deleted2}")
