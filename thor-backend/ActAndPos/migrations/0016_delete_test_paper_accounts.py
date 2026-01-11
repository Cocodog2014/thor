from __future__ import annotations

from django.db import migrations


def purge_test_paper_accounts(apps, schema_editor):
    PaperBalance = apps.get_model("ActAndPos", "PaperBalance")
    PaperPosition = apps.get_model("ActAndPos", "PaperPosition")
    PaperOrder = apps.get_model("ActAndPos", "PaperOrder")
    PaperFill = apps.get_model("ActAndPos", "PaperFill")

    # Legacy/test data sometimes used account keys like TEST-001. We only support
    # PAPER-* keys in production, so purge TEST* rows.
    PaperFill.objects.filter(account_key__istartswith="TEST").delete()
    PaperOrder.objects.filter(account_key__istartswith="TEST").delete()
    PaperPosition.objects.filter(account_key__istartswith="TEST").delete()
    PaperBalance.objects.filter(account_key__istartswith="TEST").delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("ActAndPos", "0015_remove_account_user_remove_position_account_and_more"),
    ]

    operations = [
        migrations.RunPython(purge_test_paper_accounts, noop),
    ]
