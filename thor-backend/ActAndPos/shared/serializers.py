"""Shared serializers for statement/reporting endpoints.

Scaffolding placeholder: implementations will be added as we move statement
views to ActAndPos.shared.
"""

from rest_framework import serializers


class NotImplementedSerializer(serializers.Serializer):
    detail = serializers.CharField(default="Not implemented")
