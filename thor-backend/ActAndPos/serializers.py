from rest_framework import serializers

class AccountSummarySerializer(serializers.Serializer):
    """UI-facing account summary.

    This used to be backed by legacy ActAndPos.Account. After the cutover,
    it is backed by split-domain balance rows (PaperBalance/LiveBalance) and
    a lightweight account reference.
    """

    id = serializers.CharField()
    broker = serializers.CharField()
    broker_account_id = serializers.CharField()
    account_number = serializers.CharField(allow_null=True, required=False)
    display_name = serializers.CharField(allow_blank=True, required=False)
    currency = serializers.CharField(required=False)

    net_liq = serializers.CharField(required=False)
    cash = serializers.CharField(required=False)
    starting_balance = serializers.CharField(required=False)
    current_cash = serializers.CharField(required=False)
    equity = serializers.CharField(required=False)
    stock_buying_power = serializers.CharField(required=False)
    option_buying_power = serializers.CharField(required=False)
    day_trading_buying_power = serializers.CharField(required=False)

    ok_to_trade = serializers.BooleanField(required=False)

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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        broker = str(data.get("broker") or "").upper()

        user = self.context.get("user")
        if broker == "SCHWAB" and not self._has_live_connection(user):
            for field in self.ZEROABLE_FIELDS:
                data[field] = "0.00"
            data["ok_to_trade"] = False

        return data

    def _has_live_connection(self, user) -> bool:
        if not user:
            return False

        # Preferred: use the user helper that returns a non-expired token.
        getter = getattr(user, "get_active_schwab_token", None)
        if callable(getter):
            return getter() is not None

        # Backward-compatible: user may expose a schwab_token attribute/property.
        connection = getattr(user, "schwab_token", None)
        if connection is not None:
            # Handle both a single token object and a related manager/queryset.
            if hasattr(connection, "is_expired"):
                return not getattr(connection, "is_expired", True)

            try:
                token = connection.filter(broker="SCHWAB").first()
                if token is not None:
                    return not getattr(token, "is_expired", True)
            except Exception:
                pass

        # Last resort: query BrokerConnection directly.
        try:
            from LiveData.schwab.models import BrokerConnection

            token = BrokerConnection.objects.filter(user=user, broker="SCHWAB").first()
            if token is None:
                return False
            return not getattr(token, "is_expired", True)
        except Exception:
            return False


