# Generated migration to reorder future column in database

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ThorTrading', '0012_marketopensession_future'),
    ]

    operations = [
        migrations.RunSQL(
            # Create new table with correct column order
            sql="""
                CREATE TABLE "ThorTrading_marketopensession_new" (
                    "id" serial NOT NULL PRIMARY KEY,
                    "session_number" integer NOT NULL,
                    "year" integer NOT NULL,
                    "month" integer NOT NULL,
                    "date" integer NOT NULL,
                    "day" varchar(10) NOT NULL,
                    "captured_at" timestamp with time zone NOT NULL,
                    "country" varchar(50) NOT NULL,
                    "future" varchar(10) NOT NULL,
                    "reference_open" numeric(10, 2) NULL,
                    "reference_close" numeric(10, 2) NULL,
                    "reference_ask" numeric(10, 2) NULL,
                    "reference_bid" numeric(10, 2) NULL,
                    "reference_last" numeric(10, 2) NULL,
                    "entry_price" numeric(10, 2) NULL,
                    "target_high" numeric(10, 2) NULL,
                    "target_low" numeric(10, 2) NULL,
                    "total_signal" varchar(20) NOT NULL,
                    "strong_sell_flag" boolean NOT NULL,
                    "study_fw" varchar(50) NOT NULL,
                    "fw_weight" numeric(10, 4) NULL,
                    "didnt_work" boolean NOT NULL,
                    "fw_nwdw" varchar(20) NOT NULL,
                    "fw_exit_value" numeric(10, 2) NULL,
                    "fw_exit_percent" numeric(10, 4) NULL,
                    "fw_stopped_out_value" numeric(10, 2) NULL,
                    "fw_stopped_out_nwdw" varchar(20) NOT NULL,
                    "created_at" timestamp with time zone NOT NULL,
                    "updated_at" timestamp with time zone NOT NULL,
                    UNIQUE ("country", "year", "month", "date")
                );
                
                INSERT INTO "ThorTrading_marketopensession_new" 
                SELECT 
                    id, session_number, year, month, date, day, captured_at, 
                    country, future, reference_open, reference_close, reference_ask, 
                    reference_bid, reference_last, entry_price, target_high, target_low,
                    total_signal, strong_sell_flag, study_fw, fw_weight, didnt_work, 
                    fw_nwdw, fw_exit_value, fw_exit_percent, fw_stopped_out_value, 
                    fw_stopped_out_nwdw, created_at, updated_at
                FROM "ThorTrading_marketopensession";
                
                DROP TABLE "ThorTrading_marketopensession" CASCADE;
                
                ALTER TABLE "ThorTrading_marketopensession_new" 
                RENAME TO "ThorTrading_marketopensession";
                
                -- Recreate foreign key constraints from FutureSnapshot
                ALTER TABLE "ThorTrading_futuresnapshot"
                ADD CONSTRAINT "ThorTrading_futures_session_id_fkey"
                FOREIGN KEY ("session_id") REFERENCES "ThorTrading_marketopensession"("id")
                ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
                
                -- Recreate foreign key constraints from FutureCloseSnapshot
                ALTER TABLE "ThorTrading_futureclosesnapshot"
                ADD CONSTRAINT "ThorTrading_futuresclose_session_id_fkey"
                FOREIGN KEY ("session_id") REFERENCES "ThorTrading_marketopensession"("id")
                ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
