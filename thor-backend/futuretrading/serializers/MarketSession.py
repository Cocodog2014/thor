"""
Market Open Serializers for API responses
Single-table design: each session row represents one future
"""

from rest_framework import serializers
from FutureTrading.models.MarketSession import MarketSession


class MarketOpenSessionListSerializer(serializers.ModelSerializer):
    """Serializer for list view of market open sessions"""
    
    class Meta:
        model = MarketSession
        fields = [
            'id', 'session_number', 'year', 'month', 'date', 'day', 
            'captured_at', 'country', 'future', 'country_future', 'bhs', 'wndw',
            'last_price', 'change', 'change_percent',
            'entry_price', 'target_high', 'target_low',
            'outcome', 'fw_nwdw', 'exit_price',
            'created_at'
        ]


class MarketOpenSessionDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed view of a single future at market open"""
    
    class Meta:
        model = MarketSession
        fields = [
            'id', 'session_number', 'year', 'month', 'date', 'day', 
            'captured_at', 'country', 'future', 'country_future', 'bhs', 'wndw',
            # Live price data at open
            'last_price', 'change', 'change_percent',
            'reference_ask', 'ask_size', 'reference_bid', 'bid_size',
            'volume', 'vwap', 'spread',
            # Session price data
            'reference_close', 'reference_open', 'open_vs_prev_number', 
            'open_vs_prev_percent', 'reference_last',
            # Range data
            'day_24h_low', 'day_24h_high', 'range_high_low', 'range_percent',
            'week_52_low', 'week_52_high', 'week_52_range_high_low', 'week_52_range_percent',
            # Entry and targets
            'entry_price', 'target_high', 'target_low',
            # Signal and composite
            'weighted_average', 'bhs', 'wndw', 'weight', 'sum_weighted',
            'instrument_count', 'status', 'strong_sell_flag', 'study_fw', 'fw_weight',
            # Outcome tracking
            'outcome', 'didnt_work', 'fw_nwdw', 
            'exit_price', 'exit_time', 'fw_exit_value', 'fw_exit_percent',
            'fw_stopped_out_value', 'fw_stopped_out_nwdw',
            # Close data
            'close_last_price', 'close_change', 'close_change_percent',
            'close_bid', 'close_bid_size', 'close_ask', 'close_ask_size',
            'close_volume', 'close_vwap', 'close_spread', 'close_captured_at',
            'close_weighted_average', 'close_signal', 'close_weight',
            'close_sum_weighted', 'close_instrument_count', 'close_status',
            # Timestamps
            'created_at', 'updated_at'
        ]


__all__ = [
    'MarketOpenSessionListSerializer',
    'MarketOpenSessionDetailSerializer',
]
