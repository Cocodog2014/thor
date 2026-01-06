from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("Instruments", "0016_add_userinstrumentsubscription_state"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Keep the legacy table for rollback; remove only the Django model state.
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="SchwabSubscription"),
            ],
        ),
    ]
