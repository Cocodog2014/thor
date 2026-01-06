from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    """Rename MarketTrading24Hour DB column session_group -> session_number.

    Prior migrations introduced the ORM field rename while keeping the old
    physical column name. This migration completes the change by renaming the
    actual Postgres column so the database matches the code.
    """

    dependencies = [
        ("Instruments", "0018_markettrading24hour_session_number_alias"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE public."Instruments_markettrading24hour" RENAME COLUMN "session_group" TO "session_number";',
                    reverse_sql='ALTER TABLE public."Instruments_markettrading24hour" RENAME COLUMN "session_number" TO "session_group";',
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="markettrading24hour",
                    name="session_number",
                    field=models.IntegerField(
                        db_index=True,
                        help_text="Shared key with MarketSession.session_number",
                    ),
                ),
            ],
        )
    ]
