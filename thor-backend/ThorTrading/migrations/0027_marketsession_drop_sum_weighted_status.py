from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "ThorTrading",
            "0026_marketsession_move_weight",
        ),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE "ThorTrading_marketsession" DROP COLUMN IF EXISTS "sum_weighted" CASCADE;',
            reverse_sql="",
        ),
        migrations.RunSQL(
            sql='ALTER TABLE "ThorTrading_marketsession" DROP COLUMN IF EXISTS "status" CASCADE;',
            reverse_sql="",
        ),
    ]
