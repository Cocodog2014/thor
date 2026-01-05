from __future__ import annotations

from django.db import models

from Instruments.models import Instrument


class Study(models.Model):
    # Stable identifier used by code (e.g. FUTURE_TOTAL)
    code = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=100)

    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class StudyInstrument(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name="study_instruments")
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, related_name="instrument_studies")

    order = models.IntegerField(default=0, db_index=True)

    enabled = models.BooleanField(default=True)
    weight = models.DecimalField(max_digits=6, decimal_places=2, default=1.0)

    class Meta:
        unique_together = ("study", "instrument")

    def __str__(self) -> str:
        return f"{self.study} -> {self.instrument}"
