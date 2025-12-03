from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0029_marketsession_rename_reference_close_to_session_close"),
    ]

    operations = [
        migrations.RenameField(
            model_name="marketsession",
            old_name="reference_ask",
            new_name="session_ask",
        ),
    ]
