from rest_framework import viewsets
from .models import ImportJob
from .serializers import ImportJobSerializer


class ImportJobViewSet(viewsets.ModelViewSet):
    queryset = ImportJob.objects.all()
    serializer_class = ImportJobSerializer
