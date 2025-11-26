from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("FutureTrading", "0049_move_wndw_after_bhs"),
    ]

    operations = [
        migrations.RenameField(
            model_name="marketsession",
            old_name="session_bid",
            new_name="bid_price",
        ),
        migrations.RenameField(
            model_name="marketsession",
            old_name="session_ask",
            new_name="ask_price",
        ),
    ]
