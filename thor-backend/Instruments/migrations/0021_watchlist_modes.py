from __future__ import annotations

from django.conf import settings
from django.db import migrations, models


def forwards(apps, schema_editor):
    WatchItem = apps.get_model("Instruments", "UserInstrumentWatchlistItem")
    LiveBalance = apps.get_model("ActAndPos", "LiveBalance")

    owner_user_id = int(getattr(settings, "THOR_OWNER_USER_ID", 1) or 1)

    # Owner rows become GLOBAL.
    WatchItem.objects.filter(user_id=owner_user_id).update(mode="GLOBAL")

    live_user_ids = set(LiveBalance.objects.values_list("user_id", flat=True).distinct())

    # Users with live balances: existing watchlist rows are assumed to be LIVE.
    WatchItem.objects.exclude(user_id=owner_user_id).filter(user_id__in=live_user_ids).update(mode="LIVE")

    # Everyone else: treat existing rows as PAPER.
    WatchItem.objects.exclude(user_id=owner_user_id).exclude(user_id__in=live_user_ids).update(mode="PAPER")


def backwards(apps, schema_editor):
    WatchItem = apps.get_model("Instruments", "UserInstrumentWatchlistItem")
    WatchItem.objects.update(mode="LIVE")


class Migration(migrations.Migration):
    dependencies = [
        ("ActAndPos", "0016_delete_test_paper_accounts"),
        ("Instruments", "0020_markettrading24hour_cleanup_legacy"),
    ]

    operations = [
        migrations.AddField(
            model_name="userinstrumentwatchlistitem",
            name="mode",
            field=models.CharField(
                choices=[("GLOBAL", "Global"), ("PAPER", "Paper"), ("LIVE", "Live")],
                db_index=True,
                default="LIVE",
                help_text="Watchlist scope/mode: GLOBAL (admin), PAPER, or LIVE.",
                max_length=10,
            ),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveConstraint(
            model_name="userinstrumentwatchlistitem",
            name="uniq_user_instrument_watchlist_item",
        ),
        migrations.AddConstraint(
            model_name="userinstrumentwatchlistitem",
            constraint=models.UniqueConstraint(
                fields=("user", "instrument", "mode"),
                name="uniq_user_instrument_watchlist_item_mode",
            ),
        ),
        migrations.RemoveIndex(
            model_name="userinstrumentwatchlistitem",
            name="idx_watchlist_user_order",
        ),
        migrations.AddIndex(
            model_name="userinstrumentwatchlistitem",
            index=models.Index(fields=["user", "mode", "order"], name="idx_watchlist_user_mode_order"),
        ),
    ]
