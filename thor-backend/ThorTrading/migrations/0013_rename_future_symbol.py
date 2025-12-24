# Generated manually to rename future -> symbol fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0012_marketsession_capture_kind"),
    ]

    operations = [
        migrations.RenameField(
            model_name="marketsession",
            old_name="future",
            new_name="symbol",
        ),
        migrations.RenameField(
            model_name="marketsession",
            old_name="country_future",
            new_name="country_symbol",
        ),
        migrations.RenameField(
            model_name="marketsession",
            old_name="country_future_wndw_total",
            new_name="country_symbol_wndw_total",
        ),
        migrations.AlterUniqueTogether(
            name="marketsession",
            unique_together={("capture_group", "symbol")},
        ),
        migrations.AlterModelOptions(
            name="marketsession",
            options={
                "ordering": ["-captured_at", "symbol"],
                "verbose_name": "Market Session",
                "verbose_name_plural": "Market Sessions",
            },
        ),
        migrations.RenameField(
            model_name="marketintraday",
            old_name="future",
            new_name="symbol",
        ),
        migrations.AlterUniqueTogether(
            name="marketintraday",
            unique_together={("timestamp_minute", "symbol", "country")},
        ),
    ]
