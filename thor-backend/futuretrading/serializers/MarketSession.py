"""Serializers for MarketSession with renamed 24h fields."""

from rest_framework import serializers
from FutureTrading.models.MarketSession import MarketSession


class MarketSessionBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketSession
        fields = '__all__'


class MarketSessionListSerializer(MarketSessionBaseSerializer):
    class Meta(MarketSessionBaseSerializer.Meta):
        fields = [
            'id', 'session_number', 'capture_group', 'year', 'month', 'date', 'day',
            'captured_at', 'country', 'future', 'country_future', 'weight', 'bhs',
            'wndw',
            'country_future_wndw_total',
            'strong_buy_worked', 'strong_buy_worked_percentage',
            'strong_buy_didnt_work', 'strong_buy_didnt_work_percentage',
            'buy_worked', 'buy_worked_percentage', 'buy_didnt_work', 'buy_didnt_work_percentage',
            'hold',
            'strong_sell_worked', 'strong_sell_worked_percentage',
            'strong_sell_didnt_work', 'strong_sell_didnt_work_percentage',
            'sell_worked', 'sell_worked_percentage',
            'sell_didnt_work', 'sell_didnt_work_percentage',
            'last_price',
            'market_open', 'market_high_number', 'market_high_percentage',
            'market_low_number', 'market_low_percentage',
            'market_close_number', 'market_close_percentage_high', 'market_close_percentage_low', 'market_close_vs_open_percentage',
            'market_range_number', 'market_range_percentage',
            'entry_price', 'target_high', 'target_low',
            'target_hit_at', 'target_hit_price', 'target_hit_type',
        ]


class MarketSessionDetailSerializer(MarketSessionBaseSerializer):
    class Meta(MarketSessionBaseSerializer.Meta):
        fields = [
            'id', 'session_number', 'capture_group', 'year', 'month', 'date', 'day',
            'captured_at', 'country', 'future', 'country_future', 'weight', 'bhs',
            'wndw',
            'country_future_wndw_total', 'strong_buy_worked', 'strong_buy_worked_percentage',
            'strong_buy_didnt_work', 'strong_buy_didnt_work_percentage',
            'buy_worked', 'buy_worked_percentage', 'buy_didnt_work', 'buy_didnt_work_percentage',
            'hold',
            'strong_sell_worked', 'strong_sell_worked_percentage',
            'strong_sell_didnt_work', 'strong_sell_didnt_work_percentage',
            'sell_worked', 'sell_worked_percentage',
            'sell_didnt_work', 'sell_didnt_work_percentage',
            'last_price',
            'ask_price', 'ask_size', 'bid_price', 'bid_size',
            'volume', 'vwap',
            'market_open', 'market_high_number', 'market_high_percentage',
            'market_low_number', 'market_low_percentage',
            'market_close_number', 'market_close_percentage_high', 'market_close_percentage_low', 'market_close_vs_open_percentage',
            'market_range_number', 'market_range_percentage',
            'spread',
            'prev_close_24h', 'open_price_24h', 'open_prev_diff_24h', 'open_prev_pct_24h',
            'low_24h', 'high_24h', 'range_high_low', 'range_percent',
            'week_52_low', 'week_52_high', 'week_52_range_high_low', 'week_52_range_percent',
            'entry_price', 'target_high', 'target_low',
            'target_hit_at', 'target_hit_price', 'target_hit_type',
            'weighted_average', 'instrument_count'
        ]


MarketOpenSessionListSerializer = MarketSessionListSerializer
MarketOpenSessionDetailSerializer = MarketSessionDetailSerializer

__all__ = [
    'MarketSessionBaseSerializer',
    'MarketSessionListSerializer',
    'MarketSessionDetailSerializer',
    'MarketOpenSessionListSerializer',
    'MarketOpenSessionDetailSerializer',
]
