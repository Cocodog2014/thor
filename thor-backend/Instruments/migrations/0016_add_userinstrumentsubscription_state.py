from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Instruments", "0015_alter_instrumentintraday_options"),
        ("SchwabLiveData", "0006_expand_asset_choices"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="UserInstrumentSubscription",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "symbol",
                            models.CharField(
                                help_text="Canonical symbol (e.g., NVDA, /ES, SPX)",
                                max_length=64,
                            ),
                        ),
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
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="schwab_subscriptions",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "db_table": "schwab_subscription",
                        "verbose_name": "Schwab Subscription",
                        "verbose_name_plural": "Schwab Subscriptions",
                    },
                ),
                migrations.AddConstraint(
                    model_name="userinstrumentsubscription",
                    constraint=models.UniqueConstraint(
                        fields=("user", "symbol", "asset_type"),
                        name="uniq_schwab_subscription_user_symbol_asset",
                    ),
                ),
                migrations.AddIndex(
                    model_name="userinstrumentsubscription",
                    index=models.Index(
                        fields=["user", "asset_type"],
                        name="idx_schwab_sub_user_asset",
                    ),
                ),
                migrations.AddIndex(
                    model_name="userinstrumentsubscription",
                    index=models.Index(fields=["symbol"], name="idx_schwab_sub_symbol"),
                ),
            ],
            database_operations=[],
        ),
    ]
