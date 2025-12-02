# Update country_future_wndw_total to bigint (whole-number totals)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("FutureTrading", "0064_market_close_percentage_split"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'ALTER TABLE "FutureTrading_marketsession" '
                'ALTER COLUMN country_future_wndw_total '
                'TYPE bigint USING '
                'CASE '
                'WHEN country_future_wndw_total IS NULL THEN NULL '
                'ELSE round(country_future_wndw_total)::bigint '
                'END'
            ),
            reverse_sql=(
                'ALTER TABLE "FutureTrading_marketsession" '
                'ALTER COLUMN country_future_wndw_total '
                'TYPE numeric(14,4) USING '
                'CASE '
                'WHEN country_future_wndw_total IS NULL THEN NULL '
                'ELSE country_future_wndw_total::numeric(14,4) '
                'END'
            ),
        ),
        migrations.AlterField(
            model_name="marketsession",
            name="country_future_wndw_total",
            field=models.BigIntegerField(
                blank=True,
                help_text="Historical total count for this country/future window",
                null=True,
            ),
        ),
    ]
