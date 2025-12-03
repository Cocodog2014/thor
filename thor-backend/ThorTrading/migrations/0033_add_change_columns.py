from django.db import migrations


FORWARD_SQL = r"""
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ThorTrading_marketsession'
          AND column_name = 'change'
    ) THEN
        ALTER TABLE "ThorTrading_marketsession"
        ADD COLUMN change numeric(10,2);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ThorTrading_marketsession'
          AND column_name = 'change_percent'
    ) THEN
        ALTER TABLE "ThorTrading_marketsession"
        ADD COLUMN change_percent numeric(10,4);
    END IF;
END$$;
"""

REVERSE_SQL = r"""
ALTER TABLE "ThorTrading_marketsession" DROP COLUMN IF EXISTS change_percent;
ALTER TABLE "ThorTrading_marketsession" DROP COLUMN IF EXISTS change;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("ThorTrading", "0032_reorder_last_price_after_wndw"),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, REVERSE_SQL),
    ]
