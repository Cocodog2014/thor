from rest_framework import serializers

from .models import Account, Order, Position


class AccountSummarySerializer(serializers.ModelSerializer):
    ok_to_trade = serializers.BooleanField(read_only=True)

    class Meta:
        model = Account
        fields = [
            "id",
            "broker",
            "broker_account_id",
            "display_name",
            "currency",
            "net_liq",
            "cash",
            "stock_buying_power",
            "option_buying_power",
            "day_trading_buying_power",
            "ok_to_trade",
        ]


class PositionSerializer(serializers.ModelSerializer):
    market_value = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    unrealized_pl = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    pl_percent = serializers.DecimalField(max_digits=7, decimal_places=2, read_only=True)

    class Meta:
        model = Position
        fields = [
            "id",
            "symbol",
            "description",
            "asset_type",
            "quantity",
            "avg_price",
            "mark_price",
            "market_value",
            "unrealized_pl",
            "pl_percent",
            "realized_pl_open",
            "realized_pl_day",
            "currency",
        ]


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "id",
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
            "time_filled",
            "time_canceled",
        ]
