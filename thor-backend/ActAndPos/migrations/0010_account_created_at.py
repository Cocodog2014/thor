from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ActAndPos", "0009_account_account_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name="account",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
    ]
