from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0033_add_change_columns"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="marketsession",
            name="session_last",
        ),
    ]
