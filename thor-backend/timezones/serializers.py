from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Market, USMarketStatus, MarketDataSnapshot, UserMarketWatchlist


class MarketSerializer(serializers.ModelSerializer):
    current_time = serializers.SerializerMethodField()
    market_status = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    sort_order = serializers.SerializerMethodField()
    
    class Meta:
        model = Market
        fields = [
            'id', 'country', 'display_name', 'timezone_name', 'market_open_time', 
            'market_close_time', 'status', 'is_active', 'currency',
            'current_time', 'market_status', 'sort_order', 'created_at', 'updated_at'
        ]
    
    def get_current_time(self, obj):
        return obj.get_current_market_time()
    
    def get_market_status(self, obj):
        return obj.get_market_status()
        
    def get_display_name(self, obj):
        return obj.get_display_name()
        
    def get_sort_order(self, obj):
        return obj.get_sort_order()


class USMarketStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = USMarketStatus
        fields = ['date', 'is_trading_day', 'holiday_name', 'created_at']


class MarketDataSnapshotSerializer(serializers.ModelSerializer):
    market_country = serializers.CharField(source='market.country', read_only=True)
    
    class Meta:
        model = MarketDataSnapshot
        fields = [
            'id', 'market', 'market_country', 'collected_at',
            'market_year', 'market_month', 'market_date', 'market_day',
            'market_time', 'market_status', 'utc_offset', 'dst_active',
            'is_in_trading_hours'
        ]


class UserMarketWatchlistSerializer(serializers.ModelSerializer):
    market = MarketSerializer(read_only=True)
    market_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = UserMarketWatchlist
        fields = [
            'id', 'market', 'market_id', 'display_name', 'is_primary', 
            'order', 'created_at', 'updated_at'
        ]