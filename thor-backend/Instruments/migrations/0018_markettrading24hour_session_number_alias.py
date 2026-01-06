from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    """Rename MarketTrading24Hour.session_group -> session_number (state-only).

    The underlying DB column remains named "session_group". The model field
    `session_number` maps to that column via db_column, so no database DDL is
    required here.
    """

    dependencies = [
        ("Instruments", "0017_remove_schwabsubscription_state"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameField(
                    model_name="markettrading24hour",
                    old_name="session_group",
                    new_name="session_number",
                ),
                migrations.AlterField(
                    model_name="markettrading24hour",
                    name="session_number",
                    field=models.IntegerField(
                        db_column="session_group",
                        db_index=True,
                        help_text="Shared key with MarketSession.session_number",
                    ),
                ),
                migrations.AlterUniqueTogether(
                    name="markettrading24hour",
                    unique_together={("session_number", "symbol")},
                ),
            ],
        )
    ]
