from __future__ import annotations

from rest_framework import serializers

from .models import LiveBalance, LiveOrder, LivePosition


class LiveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveBalance
        fields = [
            "broker",
            "broker_account_id",
            "currency",
            "net_liq",
            "cash",
            "equity",
            "stock_buying_power",
            "option_buying_power",
            "day_trading_buying_power",
            "updated_at",
        ]


class LivePositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LivePosition
        fields = [
            "id",
            "broker",
            "broker_account_id",
            "symbol",
            "description",
            "asset_type",
            "quantity",
            "avg_price",
            "mark_price",
            "broker_pl_day",
            "broker_pl_ytd",
            "multiplier",
            "currency",
            "updated_at",
        ]


class LiveOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveOrder
        fields = [
            "id",
            "broker",
            "broker_account_id",
            "broker_order_id",
            "status",
            "symbol",
            "asset_type",
            "side",
            "quantity",
            "order_type",
            "limit_price",
            "stop_price",
            "time_placed",
            "time_last_update",
        ]


class LiveSubmitOrderSerializer(serializers.Serializer):
    broker_account_id = serializers.CharField(max_length=128)
    broker = serializers.CharField(max_length=20, required=False, default="SCHWAB")

    symbol = serializers.CharField(max_length=32)
    asset_type = serializers.CharField(max_length=8, required=False, default="EQ")
    side = serializers.ChoiceField(choices=["BUY", "SELL"])
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)

    order_type = serializers.CharField(max_length=16, required=False, default="MKT")
    limit_price = serializers.DecimalField(max_digits=18, decimal_places=6, required=False, allow_null=True)
    stop_price = serializers.DecimalField(max_digits=18, decimal_places=6, required=False, allow_null=True)
