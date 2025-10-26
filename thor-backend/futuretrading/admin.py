from django.contrib import admin
from .models import (
    InstrumentCategory, TradingInstrument,
    SignalStatValue, ContractWeight, SignalWeight
)
from .models.MarketOpen import MarketOpenSession, FutureSnapshot


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


class FutureSnapshotInline(admin.TabularInline):
    """Inline display of all futures snapshots for a session"""
    model = FutureSnapshot
    extra = 0
    fields = ['symbol', 'last_price', 'bid', 'ask', 'weighted_average', 'signal']
    readonly_fields = ['symbol', 'last_price', 'bid', 'ask', 'weighted_average', 'signal']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(MarketOpenSession)
class MarketOpenSessionAdmin(admin.ModelAdmin):
    list_display = [
        'session_number', 'country', 'date_display', 'day', 
        'total_signal', 'fw_nwdw', 'ym_entry_price'
    ]
    list_filter = ['country', 'day', 'total_signal', 'fw_nwdw', 'year', 'month']
    search_fields = ['country', 'session_number']
    readonly_fields = ['captured_at', 'created_at', 'updated_at']
    inlines = [FutureSnapshotInline]
    
    fieldsets = (
        ('Session Info', {
            'fields': ('session_number', 'country', 'year', 'month', 'date', 'day', 'captured_at')
        }),
        ('YM Price Data', {
            'fields': ('ym_open', 'ym_close', 'ym_ask', 'ym_bid', 'ym_last')
        }),
        ('Entry & Targets', {
            'fields': ('ym_entry_price', 'ym_high_dynamic', 'ym_low_dynamic')
        }),
        ('Signal & Composite', {
            'fields': ('total_signal', 'strong_sell_flag', 'study_fw', 'fw_weight')
        }),
        ('Outcome Tracking', {
            'fields': ('fw_nwdw', 'didnt_work', 'fw_exit_value', 'fw_exit_percent')
        }),
        ('Stopped Out', {
            'fields': ('fw_stopped_out_value', 'fw_stopped_out_nwdw'),
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
    
    ordering = ['-captured_at']


@admin.register(FutureSnapshot)
class FutureSnapshotAdmin(admin.ModelAdmin):
    list_display = [
        'session', 'symbol', 'last_price', 'bid', 'ask', 
        'weighted_average', 'signal', 'change_percent'
    ]
    list_filter = ['symbol', 'session__country', 'signal']
    search_fields = ['symbol', 'session__country']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Session Link', {
            'fields': ('session', 'symbol')
        }),
        ('Live Price Data', {
            'fields': ('last_price', 'change', 'change_percent', 'bid', 'bid_size', 'ask', 'ask_size')
        }),
        ('Market Data', {
            'fields': ('volume', 'vwap', 'spread')
        }),
        ('Session Data', {
            'fields': ('open', 'close', 'open_vs_prev_number', 'open_vs_prev_percent')
        }),
        ('24-Hour Range', {
            'fields': ('day_24h_low', 'day_24h_high', 'range_high_low', 'range_percent'),
            'classes': ('collapse',)
        }),
        ('52-Week Range', {
            'fields': ('week_52_low', 'week_52_high', 'week_52_range_high_low', 'week_52_range_percent'),
            'classes': ('collapse',)
        }),
        ('Entry & Targets', {
            'fields': ('entry_price', 'high_dynamic', 'low_dynamic'),
            'classes': ('collapse',)
        }),
        ('TOTAL Composite Fields', {
            'fields': ('weighted_average', 'signal', 'weight', 'sum_weighted', 'instrument_count', 'status'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['session', 'symbol']

