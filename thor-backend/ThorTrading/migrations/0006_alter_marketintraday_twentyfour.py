from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0005_alter_futuretrading24hour_country_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="marketintraday",
            name="twentyfour",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="intraday_bars",
                to="ThorTrading.futuretrading24hour",
            ),
        ),
    ]
