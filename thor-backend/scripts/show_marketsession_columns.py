import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thor_project.settings")
django.setup()

from django.db import connection  # noqa: E402

with connection.cursor() as cursor:
    cursor.execute(
        """
                SELECT table_name, column_name, ordinal_position,
                             data_type,
                             COALESCE(character_maximum_length::text,
                                                numeric_precision::text),
                             COALESCE(numeric_scale::text, '') AS scale,
                             is_nullable,
                             COALESCE(column_default, '')
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name ILIKE '%marketsession%'
        ORDER BY table_name, ordinal_position
        """
    )
    rows = cursor.fetchall()

if not rows:
    print("No tables matching *marketsession* found in public schema.")
    sys.exit(0)

current_table = None
output_lines = []
for table_name, column_name, position, data_type, length, scale, is_nullable, default_val in rows:
    if table_name != current_table:
        current_table = table_name
        output_lines.append(f"Table: {table_name}")
    extras = []
    if length:
        if scale:
            extras.append(f"{length},{scale}")
        else:
            extras.append(length)
    extras.append('NULL' if is_nullable == 'YES' else 'NOT NULL')
    if default_val:
        extras.append(f"default={default_val}")
    extra_str = ', '.join(extras)
    output_lines.append(f"  {position:02d}: {column_name} :: {data_type} ({extra_str})")

print("\n".join(output_lines))
