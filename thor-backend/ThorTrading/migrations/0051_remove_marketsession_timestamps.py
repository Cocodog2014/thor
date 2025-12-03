from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0050_rename_session_bid_session_ask"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="marketsession",
            name="created_at",
        ),
        migrations.RemoveField(
            model_name="marketsession",
            name="updated_at",
        ),
    ]
