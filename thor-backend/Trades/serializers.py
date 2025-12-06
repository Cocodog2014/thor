from rest_framework import serializers

from .models import Trade


class TradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trade
        fields = [
            "id",
            "symbol",
            "side",
            "quantity",
            "price",
            "commission",
            "fees",
            "exec_time",
            "order",
            "account",
        ]
