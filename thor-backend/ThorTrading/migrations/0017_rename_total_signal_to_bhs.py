from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("ThorTrading", "0016_rename_marketopensession_marketsession_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="marketsession",
            old_name="total_signal",
            new_name="bhs",
        ),
    ]
