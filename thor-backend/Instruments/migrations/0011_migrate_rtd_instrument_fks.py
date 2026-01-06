from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


def _resolve_or_create_instrument(apps, trading_instrument):
    Instrument = apps.get_model("Instruments", "Instrument")
    InstrumentCategory = apps.get_model("Instruments", "InstrumentCategory")

    raw_symbol = (getattr(trading_instrument, "symbol", "") or "").strip()
    symbol_upper = raw_symbol.upper()
    base = symbol_upper.lstrip("/")

    candidates = [symbol_upper]
    if base:
        candidates.extend([base, f"/{base}"])

    # Try to find an existing canonical Instrument first
    for sym in candidates:
        if not sym:
            continue
        found = Instrument.objects.filter(symbol__iexact=sym).first()
        if found:
            return found

    # Create missing Instrument (best-effort mapping)
    category_name = ""
    try:
        if getattr(trading_instrument, "category_id", None):
            category_name = (
                InstrumentCategory.objects.filter(pk=trading_instrument.category_id)
                .values_list("name", flat=True)
                .first()
                or ""
            )
    except Exception:
        category_name = ""

    asset_type = "FUTURE" if symbol_upper.startswith("/") or "future" in category_name.lower() else "EQUITY"

    created = Instrument.objects.create(
        symbol=symbol_upper,
        asset_type=asset_type,
        name=(getattr(trading_instrument, "name", "") or "")[:128],
        exchange=getattr(trading_instrument, "exchange", "") or "",
        currency=getattr(trading_instrument, "currency", "") or "USD",
        country=getattr(trading_instrument, "country", "") or "",
        sort_order=getattr(trading_instrument, "sort_order", 0) or 0,
        display_precision=getattr(trading_instrument, "display_precision", 2) or 2,
        tick_size=getattr(trading_instrument, "tick_size", None),
        point_value=getattr(trading_instrument, "contract_size", None),
        margin_requirement=getattr(trading_instrument, "margin_requirement", None),
        is_active=bool(getattr(trading_instrument, "is_active", True)),
    )
    return created


def forward_fill_instrument2(apps, schema_editor):
    TradingInstrument = apps.get_model("Instruments", "TradingInstrument")
    SignalStatValue = apps.get_model("Instruments", "SignalStatValue")
    ContractWeight = apps.get_model("Instruments", "ContractWeight")

    # Build mapping TradingInstrument.pk -> Instrument.pk (collisions are expected when
    # multiple countries share the same underlying symbol).
    mapping: dict[int, int] = {}
    instrument_to_trading: dict[int, list[int]] = {}

    for ti in TradingInstrument.objects.all().only(
        "id",
        "symbol",
        "country",
        "name",
        "exchange",
        "currency",
        "is_active",
        "sort_order",
        "display_precision",
        "tick_size",
        "contract_size",
        "margin_requirement",
        "category_id",
    ):
        inst = _resolve_or_create_instrument(apps, ti)
        mapping[int(ti.id)] = int(inst.id)
        instrument_to_trading.setdefault(int(inst.id), []).append(int(ti.id))

    # If multiple TradingInstrument rows map to the same Instrument, we collapse
    # the RTD config tables to one set of rows per Instrument.
    for inst_id, ti_ids in instrument_to_trading.items():
        if len(ti_ids) <= 1:
            continue

        # 1) SignalStatValue: must have at most 1 row per (instrument, signal)
        # Keep the smallest id; delete duplicates only if values match.
        rows = list(
            SignalStatValue.objects.filter(instrument_id__in=ti_ids)
            .values("id", "instrument_id", "signal", "value")
            .order_by("signal", "id")
        )

        by_signal: dict[str, list[dict]] = {}
        for r in rows:
            sig = str(r["signal"])
            by_signal.setdefault(sig, []).append(r)

        for sig, sig_rows in by_signal.items():
            if len(sig_rows) <= 1:
                continue

            # Compare values for consistency
            distinct_vals = set()
            for r in sig_rows:
                try:
                    distinct_vals.add(str(r["value"]))
                except Exception:
                    distinct_vals.add(repr(r["value"]))

            if len(distinct_vals) > 1:
                raise RuntimeError(
                    "Cannot migrate RTD SignalStatValue: conflicting values for "
                    f"Instrument#{inst_id} signal={sig} across TradingInstrument ids={ti_ids}. "
                    f"Distinct values={sorted(distinct_vals)}"
                )

            keep_id = int(sig_rows[0]["id"])
            delete_ids = [int(r["id"]) for r in sig_rows[1:]]
            if delete_ids:
                SignalStatValue.objects.filter(id__in=delete_ids).delete()

        # 2) ContractWeight: must have at most 1 row per Instrument
        cw_rows = list(
            ContractWeight.objects.filter(instrument_id__in=ti_ids)
            .values("id", "instrument_id", "weight")
            .order_by("id")
        )
        if len(cw_rows) > 1:
            distinct_w = set()
            for r in cw_rows:
                try:
                    distinct_w.add(str(r["weight"]))
                except Exception:
                    distinct_w.add(repr(r["weight"]))
            if len(distinct_w) > 1:
                raise RuntimeError(
                    "Cannot migrate RTD ContractWeight: conflicting weights for "
                    f"Instrument#{inst_id} across TradingInstrument ids={ti_ids}. "
                    f"Distinct weights={sorted(distinct_w)}"
                )

            keep_id = int(cw_rows[0]["id"])
            delete_ids = [int(r["id"]) for r in cw_rows[1:]]
            if delete_ids:
                ContractWeight.objects.filter(id__in=delete_ids).delete()

    # Populate SignalStatValue.instrument2
    for inst_id, ti_ids in instrument_to_trading.items():
        SignalStatValue.objects.filter(
            instrument_id__in=ti_ids,
            instrument2_id__isnull=True,
        ).update(instrument2_id=inst_id)

    # Populate ContractWeight.instrument2
    for inst_id, ti_ids in instrument_to_trading.items():
        ContractWeight.objects.filter(
            instrument_id__in=ti_ids,
            instrument2_id__isnull=True,
        ).update(instrument2_id=inst_id)

    # If there are still rows without instrument2 mapping, they are orphaned or
    # unmappable (e.g. instrument_id points to missing TradingInstrument). These
    # rows would fail the subsequent NOT NULL enforcement; delete them.
    missing_signal_qs = SignalStatValue.objects.filter(instrument2_id__isnull=True)
    missing_contract_qs = ContractWeight.objects.filter(instrument2_id__isnull=True)

    missing_signal_count = missing_signal_qs.count()
    missing_contract_count = missing_contract_qs.count()

    if missing_signal_count or missing_contract_count:
        missing_signal_qs.delete()
        missing_contract_qs.delete()

        # Keep a breadcrumb in the migration output (safe in non-interactive runs).
        print(
            "RTD migration warning: deleted unmappable rows: "
            f"SignalStatValue={missing_signal_count} ContractWeight={missing_contract_count}"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("Instruments", "0010_alter_signalstatvalue_signal_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="signalstatvalue",
            name="instrument2",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="Instruments.instrument",
            ),
        ),
        migrations.AddField(
            model_name="contractweight",
            name="instrument2",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="Instruments.instrument",
            ),
        ),
        migrations.RunPython(forward_fill_instrument2, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name="signalstatvalue",
            name="instrument2",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="Instruments.instrument",
            ),
        ),
        migrations.AlterField(
            model_name="contractweight",
            name="instrument2",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="Instruments.instrument",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="signalstatvalue",
            unique_together={("instrument2", "signal")},
        ),
        # NOTE: This data migration is effectively irreversible (reverse_code=noop).
        # When migrating backwards, Django would normally try to re-add the removed
        # NOT NULL instrument_id columns, which fails on existing rows (NULLs).
        # We keep state changes the same, but make the DB operations rollback-safe.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="signalstatvalue",
                    name="instrument",
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE "Instruments_signalstatvalue" DROP COLUMN IF EXISTS "instrument_id";',
                    reverse_sql='ALTER TABLE "Instruments_signalstatvalue" ADD COLUMN IF NOT EXISTS "instrument_id" BIGINT NULL;',
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="contractweight",
                    name="instrument",
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE "Instruments_contractweight" DROP COLUMN IF EXISTS "instrument_id";',
                    reverse_sql='ALTER TABLE "Instruments_contractweight" ADD COLUMN IF NOT EXISTS "instrument_id" BIGINT NULL;',
                ),
            ],
        ),
        migrations.RenameField(
            model_name="signalstatvalue",
            old_name="instrument2",
            new_name="instrument",
        ),
        migrations.RenameField(
            model_name="contractweight",
            old_name="instrument2",
            new_name="instrument",
        ),
        migrations.AlterUniqueTogether(
            name="signalstatvalue",
            unique_together={("instrument", "signal")},
        ),
    ]
