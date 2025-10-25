#!/usr/bin/env python
"""Create migration file to drop unused tables"""
import os

migration_content = """# Generated manually to drop unused tables
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("FutureTrading", "0003_delete_hbsthresholds"),
    ]

    operations = [
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS "FutureTrading_marketdata" CASCADE;',
            reverse_sql="",
        ),
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS "FutureTrading_tradingsignal" CASCADE;',
            reverse_sql="",
        ),
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS "FutureTrading_watchlistitem" CASCADE;',
            reverse_sql="",
        ),
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS "FutureTrading_watchlistgroup" CASCADE;',
            reverse_sql="",
        ),
    ]
"""

filepath = r"a:\Thor\thor-backend\FutureTrading\migrations\0004_remove_unused_models.py"
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(migration_content)

print(f"Created migration file: {filepath}")
