from django.db import models
from Instruments.models import Instrument
from ThorTrading.studies.models.study import Study  # or wherever Study lives

class StudyInstrument(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name="study_instruments")
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, related_name="study_links")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        unique_together = ("study", "instrument")
        ordering = ("sort_order", "id")
