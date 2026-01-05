# ThorTrading/models/studies.py (example)
from django.db import models
from Instruments.models import Instrument

class Study(models.Model):
    code = models.CharField(max_length=64, unique=True)  # "FUTURE_TOTAL"
    name = models.CharField(max_length=128, default="Future Total")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

class StudyInstrument(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name="study_instruments")
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, related_name="instrument_studies")
    enabled = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("study", "instrument"), name="uniq_study_instrument"),
        ]
        indexes = [
            models.Index(fields=["study", "order"], name="idx_study_order"),
        ]

    def __str__(self):
        return f"{self.study.code}:{self.instrument.symbol}"
