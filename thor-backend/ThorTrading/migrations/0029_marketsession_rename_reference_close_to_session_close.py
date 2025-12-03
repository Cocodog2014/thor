from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0028_marketsession_rename_reference_open_to_session_open"),
    ]

    operations = [
        migrations.RenameField(
            model_name="marketsession",
            old_name="reference_close",
            new_name="session_close",
        ),
    ]
