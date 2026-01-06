from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("SchwabLiveData", "0006_expand_asset_choices"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="SchwabSubscription"),
            ],
            database_operations=[],
        ),
    ]
