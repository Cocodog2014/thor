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
            'market_open', 'market_high_open', 'market_high_pct_open',
            'market_low_open', 'market_low_pct_open',
            'market_close', 'market_high_pct_close', 'market_low_pct_close', 'market_close_vs_open_percentage',
            'market_range', 'market_range_pct',
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
            'market_open', 'market_high_open', 'market_high_pct_open',
            'market_low_open', 'market_low_pct_open',
            'market_close', 'market_high_pct_close', 'market_low_pct_close', 'market_close_vs_open_percentage',
            'market_range', 'market_range_pct',
            'spread',
            'prev_close_24h', 'open_price_24h', 'open_prev_diff_24h', 'open_prev_pct_24h',
            'low_24h', 'high_24h', 'range_diff_24h', 'range_pct_24h',
            'low_52w', 'low_pct_52w', 'high_52w', 'high_pct_52w', 'range_52w', 'range_pct_52w',
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
