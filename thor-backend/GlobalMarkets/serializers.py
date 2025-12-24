from rest_framework import serializers
from .models import Market, USMarketStatus, MarketDataSnapshot, UserMarketWatchlist


class MarketSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    sort_order = serializers.SerializerMethodField()

    class Meta:
        model = Market
        fields = [
            "id",
            "country",
            "display_name",
            "timezone_name",
            "market_open_time",
            "market_close_time",
            "status",
            "is_active",
            "currency",
            "enable_futures_capture",
            "enable_open_capture",
            "enable_close_capture",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_display_name(self, obj):
        return obj.get_display_name()

    def get_sort_order(self, obj):
        return obj.get_sort_order()


class USMarketStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = USMarketStatus
        fields = ["id", "date", "is_trading_day", "holiday_name", "created_at"]
        read_only_fields = ["id", "created_at"]


class MarketDataSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketDataSnapshot
        fields = [
            "id",
            "market",
            "market_year",
            "market_month",
            "market_date",
            "market_day",
            "market_time",
            "market_status",
            "utc_offset",
            "dst_active",
            "is_in_trading_hours",
            "collected_at",
        ]
        read_only_fields = ["id", "collected_at"]


class UserMarketWatchlistSerializer(serializers.ModelSerializer):
    market = MarketSerializer(read_only=True)
    market_id = serializers.PrimaryKeyRelatedField(
        source="market",
        queryset=Market.objects.all(),
        write_only=True,
    )

    class Meta:
        model = UserMarketWatchlist
        fields = [
            "id",
            "market",
            "market_id",
            "display_name",
            "is_primary",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
