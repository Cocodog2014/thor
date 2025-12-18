from rest_framework import serializers

from .models import Account, Order, Position


class AccountSummarySerializer(serializers.ModelSerializer):
    ok_to_trade = serializers.BooleanField(read_only=True)

    ZEROABLE_FIELDS = [
        "net_liq",
        "cash",
        "starting_balance",
        "current_cash",
        "equity",
        "stock_buying_power",
        "option_buying_power",
        "day_trading_buying_power",
    ]

    class Meta:
        model = Account
        fields = [
            "id",
            "broker",
            "broker_account_id",
            "account_number",
            "display_name",
            "currency",
            "net_liq",
            "cash",
            "starting_balance",
            "current_cash",
            "equity",
            "stock_buying_power",
            "option_buying_power",
            "day_trading_buying_power",
            "ok_to_trade",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.broker == "SCHWAB" and not self._has_live_connection(instance):
            for field in self.ZEROABLE_FIELDS:
                data[field] = "0.00"
            data["ok_to_trade"] = False

        return data

    def _has_live_connection(self, instance) -> bool:
        user = getattr(instance, "user", None)
        if not user:
            return False

        connection = getattr(user, "schwab_token", None)
        if connection is None:
            return False

        return not connection.is_expired


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

