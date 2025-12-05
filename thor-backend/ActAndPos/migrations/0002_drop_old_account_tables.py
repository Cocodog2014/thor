from django.db import migrations

DROP_OLD_ACCOUNT_TABLES = """
DROP TABLE IF EXISTS account_statement_accountsummary CASCADE;
DROP TABLE IF EXISTS account_statement_paperaccount CASCADE;
DROP TABLE IF EXISTS account_statement_realaccount CASCADE;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("ActAndPos", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=DROP_OLD_ACCOUNT_TABLES,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
