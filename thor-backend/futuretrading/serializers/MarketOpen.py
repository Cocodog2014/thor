"""
Market Open Serializers for API responses
"""

from rest_framework import serializers
from FutureTrading.models.MarketOpen import MarketOpenSession, FutureSnapshot


class FutureSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for individual future snapshot data"""
    
    class Meta:
        model = FutureSnapshot
        fields = [
            'id', 'symbol', 'last_price', 'change', 'change_percent',
            'bid', 'bid_size', 'ask', 'ask_size',
            'volume', 'vwap', 'spread',
            'open', 'close', 'open_vs_prev_number', 'open_vs_prev_percent',
            'day_24h_low', 'day_24h_high', 'range_high_low', 'range_percent',
            'week_52_low', 'week_52_high', 'week_52_range_high_low', 'week_52_range_percent',
            'entry_price', 'high_dynamic', 'low_dynamic',
            'weighted_average', 'signal', 'weight', 'sum_weighted', 
            'instrument_count', 'status',
            'outcome', 'exit_price', 'exit_time',
            'created_at'
        ]


class MarketOpenSessionListSerializer(serializers.ModelSerializer):
    """Serializer for list view of market open sessions"""
    
    class Meta:
        model = MarketOpenSession
        fields = [
            'id', 'session_number', 'year', 'month', 'date', 'day', 
            'captured_at', 'country', 'total_signal', 
            'ym_entry_price', 'ym_high_dynamic', 'ym_low_dynamic',
            'fw_nwdw', 'fw_exit_value', 'fw_exit_percent',
            'created_at'
        ]


class MarketOpenSessionDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed view with all futures data"""
    futures = FutureSnapshotSerializer(many=True, read_only=True)
    
    class Meta:
        model = MarketOpenSession
        fields = [
            'id', 'session_number', 'year', 'month', 'date', 'day', 
            'captured_at', 'country',
            'ym_open', 'ym_close', 'ym_ask', 'ym_bid', 'ym_last',
            'ym_entry_price', 'ym_high_dynamic', 'ym_low_dynamic',
            'total_signal', 'strong_sell_flag', 'study_fw', 'fw_weight',
            'didnt_work', 'fw_nwdw', 
            'fw_exit_value', 'fw_exit_percent',
            'fw_stopped_out_value', 'fw_stopped_out_nwdw',
            'futures',
            'created_at', 'updated_at'
        ]


__all__ = [
    'FutureSnapshotSerializer',
    'MarketOpenSessionListSerializer',
    'MarketOpenSessionDetailSerializer',
]
