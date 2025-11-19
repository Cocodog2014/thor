from django.contrib import admin
from .models import (
    InstrumentCategory, TradingInstrument,
    SignalStatValue, ContractWeight, SignalWeight
)
from .models.MarketSession import MarketSession
from .models.extremes import Rolling52WeekStats


class SignalStatValueInline(admin.TabularInline):
    model = SignalStatValue
    extra = 0
    fields = ['signal', 'value']


class ContractWeightInline(admin.StackedInline):
    model = ContractWeight
    extra = 0
    fields = ['weight']


@admin.register(InstrumentCategory)
class InstrumentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'is_active', 'sort_order']
    list_filter = ['is_active']
    list_editable = ['is_active', 'sort_order']
    search_fields = ['name', 'display_name']


@admin.register(TradingInstrument)
class TradingInstrumentAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'category', 'exchange', 'is_active', 'is_watchlist']
    list_filter = ['category', 'is_active', 'is_watchlist', 'exchange']
    list_editable = ['is_active', 'is_watchlist']
    search_fields = ['symbol', 'name']
    inlines = [SignalStatValueInline, ContractWeightInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('symbol', 'name', 'description', 'category')
        }),
        ('Market Information', {
            'fields': ('exchange', 'currency')
        }),
        ('Trading Configuration', {
            'fields': ('is_active', 'is_watchlist', 'sort_order')
        }),
        ('Display Configuration', {
            'fields': ('display_precision', 'tick_size', 'contract_size')
        }),
        ('API Configuration', {
            'fields': ('api_provider', 'api_symbol', 'update_frequency')
        }),
    )


@admin.register(SignalStatValue)
class SignalStatValueAdmin(admin.ModelAdmin):
    list_display = ['instrument', 'signal', 'value']
    list_filter = ['signal', 'instrument__category']
    search_fields = ['instrument__symbol', 'instrument__name']
    list_editable = ['value']


@admin.register(ContractWeight)
class ContractWeightAdmin(admin.ModelAdmin):
    list_display = ['instrument', 'weight']
    list_filter = ['instrument__category']
    search_fields = ['instrument__symbol', 'instrument__name']
    list_editable = ['weight']


@admin.register(SignalWeight)
class SignalWeightAdmin(admin.ModelAdmin):
    list_display = ['signal', 'weight']
    list_filter = ['signal']
    list_editable = ['weight']
    ordering = ['-weight']


# Market Open Capture Admin


@admin.register(MarketSession)
class MarketSessionAdmin(admin.ModelAdmin):
    list_display = [
        'session_number', 'country', 'future', 'country_future', 'date_display', 'day', 
        'bhs', 'wndw', 'fw_nwdw', 'entry_price', 'last_price'
    ]
    list_filter = ['country', 'future', 'day', 'bhs', 'wndw', 'fw_nwdw', 'year', 'month']
    search_fields = ['country', 'session_number', 'future']
    readonly_fields = ['captured_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Session Info', {
            'fields': ('session_number', 'country', 'future', 'country_future', 'year', 'month', 'date', 'day', 'captured_at')
        }),
        ('Live Price Data (Open)', {
            'fields': ('last_price', 'change', 'change_percent', 'session_ask', 'ask_size', 
                      'session_bid', 'bid_size', 'volume', 'vwap', 'spread')
        }),
        ('Session Price Data', {
            'fields': ('session_close', 'session_open', 'open_vs_prev_number', 'open_vs_prev_percent', 'session_last')
        }),
        ('Range Data', {
            'fields': ('day_24h_low', 'day_24h_high', 'range_high_low', 'range_percent',
                      'week_52_low', 'week_52_high', 'week_52_range_high_low', 'week_52_range_percent'),
            'classes': ('collapse',)
        }),
        ('Entry & Targets', {
            'fields': ('entry_price', 'target_high', 'target_low')
        }),
        ('Signal & Composite', {
            'fields': (
                'bhs', 'wndw', 'country_future_wndw_total',
                'strong_buy_worked', 'strong_buy_worked_percentage',
                'strong_buy_didnt_work', 'strong_buy_didnt_work_percentage',
                'buy_worked', 'buy_worked_percentage', 'buy_didnt_work', 'buy_didnt_work_percentage',
                'hold', 'hold_percentage',
                'strong_sell_worked', 'strong_sell_worked_percentage',
                'strong_sell_didnt_work', 'strong_sell_didnt_work_percentage',
                    'sell_worked', 'sell_worked_percentage',
                    'sell_didnt_work', 'sell_didnt_work_percentage',
                    'weighted_average', 'weight',
                        'instrument_count', 'strong_sell_flag', 'study_fw', 'fw_weight')
        }),
        ('Outcome Tracking', {
            'fields': ('outcome', 'fw_nwdw', 'didnt_work', 'exit_price', 'exit_time',
                      'fw_exit_value', 'fw_exit_percent')
        }),
        ('Stopped Out', {
            'fields': ('fw_stopped_out_value', 'fw_stopped_out_nwdw'),
            'classes': ('collapse',)
        }),
        ('Close Data', {
            'fields': ('close_last_price', 'close_change', 'close_change_percent',
                      'close_bid', 'close_bid_size', 'close_ask', 'close_ask_size',
                      'close_volume', 'close_vwap', 'close_spread', 'close_captured_at',
                      'close_weighted_average', 'close_signal', 'close_weight',
                      'close_sum_weighted', 'close_instrument_count', 'close_status'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def date_display(self, obj):
        return f"{obj.year}/{obj.month:02d}/{obj.date:02d}"
    date_display.short_description = 'Date'
    
    ordering = ['-captured_at', 'future']


# 52-Week High/Low Tracking Admin


@admin.register(Rolling52WeekStats)
class Rolling52WeekStatsAdmin(admin.ModelAdmin):
    """
    Admin interface for managing 52-week high/low extremes.
    
    Usage:
    1. Seed initial values for each symbol (one-time setup)
    2. System automatically updates when new highs/lows occur
    3. Monitor last_price_checked to see if system is updating
    """
    list_display = [
        'symbol', 
        'high_52w', 'high_52w_date',
        'low_52w', 'low_52w_date',
        'last_price_checked',
        'last_updated'
    ]
    list_filter = ['high_52w_date', 'low_52w_date']
    search_fields = ['symbol']
    readonly_fields = ['last_price_checked', 'last_updated', 'created_at']
    ordering = ['symbol']
    
    fieldsets = (
        ('Symbol', {
            'fields': ('symbol',)
        }),
        ('52-Week High', {
            'fields': ('high_52w', 'high_52w_date'),
            'description': 'Enter initial 52-week high. System will auto-update when exceeded.'
        }),
        ('52-Week Low', {
            'fields': ('low_52w', 'low_52w_date'),
            'description': 'Enter initial 52-week low. System will auto-update when breached.'
        }),
        ('All-Time Extremes (Optional)', {
            'fields': ('all_time_high', 'all_time_high_date', 'all_time_low', 'all_time_low_date'),
            'classes': ('collapse',),
            'description': 'Leave blank to track automatically, or enter known values.'
        }),
        ('System Tracking', {
            'fields': ('last_price_checked', 'last_updated', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """When creating new record, set dates to today if not provided"""
        if not change:  # New record
            from django.utils import timezone
            today = timezone.now().date()
            if not obj.high_52w_date:
                obj.high_52w_date = today
            if not obj.low_52w_date:
                obj.low_52w_date = today
        super().save_model(request, obj, form, change)


