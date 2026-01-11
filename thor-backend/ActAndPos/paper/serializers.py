from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from .models import PaperBalance, PaperOrder, PaperPosition


class PaperBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperBalance
        fields = [
            "account_key",
            "currency",
            "cash",
            "equity",
            "net_liq",
            "buying_power",
            "day_trade_bp",
            "updated_at",
        ]


class PaperPositionSerializer(serializers.ModelSerializer):
    market_value = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = PaperPosition
        fields = [
            "id",
            "account_key",
            "symbol",
            "description",
            "asset_type",
            "quantity",
            "avg_price",
            "mark_price",
            "market_value",
            "realized_pl_day",
            "realized_pl_total",
            "currency",
            "updated_at",
        ]


class PaperOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperOrder
        fields = [
            "id",
            "account_key",
            "client_order_id",
            "symbol",
            "asset_type",
            "side",
            "quantity",
            "order_type",
            "limit_price",
            "stop_price",
            "status",
            "time_placed",
            "time_last_update",
        ]


class PaperSubmitOrderSerializer(serializers.Serializer):
    account_key = serializers.CharField(max_length=64)
    client_order_id = serializers.CharField(max_length=64, required=False, allow_blank=True)

    symbol = serializers.CharField(max_length=32)
    asset_type = serializers.CharField(max_length=8, required=False, default="EQ")
    side = serializers.ChoiceField(choices=["BUY", "SELL"])
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)

    order_type = serializers.CharField(max_length=16, required=False, default="MKT")
    limit_price = serializers.DecimalField(max_digits=18, decimal_places=6, required=False, allow_null=True)
    stop_price = serializers.DecimalField(max_digits=18, decimal_places=6, required=False, allow_null=True)

    commission = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=Decimal("0"))
    fees = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=Decimal("0"))
