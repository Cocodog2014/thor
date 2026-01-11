from rest_framework import serializers


class NotImplementedSerializer(serializers.Serializer):
    detail = serializers.CharField(default="Not implemented")
