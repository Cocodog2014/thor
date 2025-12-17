from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ActAndPos", "0008_accountdailysnapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="account_number",
            field=models.CharField(
                blank=True,
                max_length=32,
                null=True,
                help_text="Broker-provided account number (non-unique).",
            ),
        ),
    ]
