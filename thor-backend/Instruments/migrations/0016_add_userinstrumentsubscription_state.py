from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Instruments", "0015_alter_instrumentintraday_options"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SchwabSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("symbol", models.CharField(help_text="Canonical symbol (e.g., NVDA, /ES, SPX)", max_length=64)),
                (
                    "asset_type",
                    models.CharField(
                        choices=[
                            ("EQUITY", "Equity"),
                            ("FUTURE", "Future"),
                            ("INDEX", "Index"),
                            ("OPTION", "Option"),
                            ("BOND", "Bond"),
                            ("FOREX", "Forex"),
                            ("MUTUAL_FUND", "Mutual Fund"),
                        ],
                        default="EQUITY",
                        help_text="Asset class used to route to the proper streaming service",
                        max_length=16,
                    ),
                ),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        help_text="Owner of this Schwab streaming subscription",
                        on_delete=models.deletion.CASCADE,
                        related_name="schwab_subscriptions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "instrument_schwab_subscription",
                "verbose_name": "Schwab Subscription",
                "verbose_name_plural": "Schwab Subscriptions",
            },
        ),
        migrations.AddConstraint(
            model_name="schwabsubscription",
            constraint=models.UniqueConstraint(
                fields=("user", "symbol", "asset_type"),
                name="uq_isub_usr_sym_ast",
            ),
        ),
        migrations.AddIndex(
            model_name="schwabsubscription",
            index=models.Index(fields=["user", "asset_type"], name="ix_isub_usr_ast"),
        ),
        migrations.AddIndex(
            model_name="schwabsubscription",
            index=models.Index(fields=["symbol"], name="ix_isub_sym"),
        ),
    ]
