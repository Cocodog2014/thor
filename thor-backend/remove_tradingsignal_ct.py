#!/usr/bin/env python
"""Remove obsolete TradingSignal content type"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.contenttypes.models import ContentType

# Delete TradingSignal content type
deleted = ContentType.objects.filter(app_label='FutureTrading', model='tradingsignal').delete()
print(f"Deleted TradingSignal content type: {deleted}")
