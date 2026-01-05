from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("Instruments", "0005_markettrading24hour_unmanaged"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="InstrumentCategory",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=50, unique=True)),
                        ("display_name", models.CharField(max_length=100)),
                        ("description", models.TextField(blank=True)),
                        ("is_active", models.BooleanField(default=True)),
                        ("sort_order", models.IntegerField(default=0)),
                        ("color_primary", models.CharField(default="#4CAF50", max_length=7)),
                        ("color_secondary", models.CharField(default="#81C784", max_length=7)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        "managed": False,
                        "db_table": "ThorTrading_instrumentcategory",
                        "ordering": ["sort_order", "name"],
                        "verbose_name": "Instrument Category",
                        "verbose_name_plural": "Instrument Categories",
                    },
                ),
                migrations.CreateModel(
                    name="TradingInstrument",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("country", models.CharField(db_index=True, max_length=32)),
                        ("symbol", models.CharField(db_index=True, max_length=50)),
                        ("name", models.CharField(max_length=200)),
                        ("description", models.TextField(blank=True)),
                        ("exchange", models.CharField(blank=True, max_length=50)),
                        ("currency", models.CharField(default="USD", max_length=10)),
                        ("is_active", models.BooleanField(db_index=True, default=True)),
                        ("is_watchlist", models.BooleanField(default=False)),
                        ("show_in_ribbon", models.BooleanField(default=False)),
                        ("sort_order", models.IntegerField(default=0)),
                        ("display_precision", models.IntegerField(default=2)),
                        ("tick_size", models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True)),
                        ("contract_size", models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                        ("tick_value", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                        ("margin_requirement", models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                        ("api_provider", models.CharField(blank=True, max_length=50)),
                        ("api_symbol", models.CharField(blank=True, max_length=100)),
                        ("feed_symbol", models.CharField(blank=True, max_length=100)),
                        ("update_frequency", models.IntegerField(default=5)),
                        ("last_updated", models.DateTimeField(blank=True, null=True)),
                        ("is_market_open", models.BooleanField(default=False)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        (
                            "category",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="instruments",
                                to="Instruments.instrumentcategory",
                            ),
                        ),
                    ],
                    options={
                        "managed": False,
                        "db_table": "ThorTrading_tradinginstrument",
                        "ordering": ["sort_order", "country", "symbol"],
                        "verbose_name": "Trading Instrument",
                        "verbose_name_plural": "Trading Instruments",
                        "indexes": [
                            models.Index(fields=["country", "symbol"], name="idx_instr_country_symbol"),
                            models.Index(fields=["country", "is_active"], name="idx_instr_country_active"),
                            models.Index(fields=["category", "sort_order"], name="idx_instr_category_sort"),
                        ],
                        "unique_together": {("country", "symbol")},
                    },
                ),
                migrations.CreateModel(
                    name="SignalWeight",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("signal", models.CharField(max_length=20, unique=True)),
                        ("weight", models.IntegerField(help_text="Weight value for this signal type")),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        "managed": False,
                        "db_table": "ThorTrading_signalweight",
                        "ordering": ["-weight"],
                        "verbose_name": "Signal Weight",
                        "verbose_name_plural": "Signal Weights",
                    },
                ),
                migrations.CreateModel(
                    name="SignalStatValue",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("signal", models.CharField(max_length=20)),
                        ("value", models.DecimalField(decimal_places=6, max_digits=10)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        (
                            "instrument",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="signal_stat_values",
                                to="Instruments.tradinginstrument",
                            ),
                        ),
                    ],
                    options={
                        "managed": False,
                        "db_table": "ThorTrading_signalstatvalue",
                        "ordering": ["instrument__country", "instrument__symbol", "signal"],
                        "verbose_name": "Signal Statistical Value",
                        "verbose_name_plural": "Signal Statistical Values",
                        "unique_together": {("instrument", "signal")},
                    },
                ),
                migrations.CreateModel(
                    name="ContractWeight",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("weight", models.DecimalField(decimal_places=6, default=1.0, max_digits=8)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        (
                            "instrument",
                            models.OneToOneField(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="contract_weight",
                                to="Instruments.tradinginstrument",
                            ),
                        ),
                    ],
                    options={
                        "managed": False,
                        "db_table": "ThorTrading_contractweight",
                        "ordering": ["instrument__country", "instrument__symbol"],
                        "verbose_name": "Contract Weight",
                        "verbose_name_plural": "Contract Weights",
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
