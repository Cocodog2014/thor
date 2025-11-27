from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("FutureTrading", "0066_remove_marketsession_hold_percentage_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="marketsession",
            old_name="session_close",
            new_name="prev_close_24h",
        ),
        migrations.RenameField(
            model_name="marketsession",
            old_name="session_open",
            new_name="open_price_24h",
        ),
        migrations.RenameField(
            model_name="marketsession",
            old_name="open_vs_prev_number",
            new_name="open_prev_diff_24h",
        ),
        migrations.RenameField(
            model_name="marketsession",
            old_name="open_vs_prev_percent",
            new_name="open_prev_pct_24h",
        ),
    ]
