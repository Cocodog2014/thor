from decimal import Decimal

from django.db import migrations, models


def seed_paper_accounts(apps, schema_editor):
    Account = apps.get_model("ActAndPos", "Account")
    default_balance = Decimal("100000.00")

    for account in Account.objects.filter(broker="PAPER"):
        updated_fields = []

        if not account.starting_balance:
            account.starting_balance = default_balance
            updated_fields.append("starting_balance")

        if not account.cash:
            account.cash = default_balance
            updated_fields.append("cash")

        if not account.net_liq:
            account.net_liq = default_balance
            updated_fields.append("net_liq")

        if not account.current_cash:
            account.current_cash = account.cash or default_balance
            updated_fields.append("current_cash")

        if not account.equity:
            account.equity = account.net_liq or default_balance
            updated_fields.append("equity")

        if updated_fields:
            account.save(update_fields=updated_fields)


def noop(apps, schema_editor):
    """Reverse operation placeholder."""


class Migration(migrations.Migration):
    dependencies = [
        ("ActAndPos", "0003_delete_trade"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="current_cash",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="account",
            name="equity",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="account",
            name="starting_balance",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
        migrations.RunPython(seed_paper_accounts, noop),
    ]
