from __future__ import annotations
from django.contrib import admin
from GlobalMarkets.services.active_markets import get_control_countries
from GlobalMarkets.services.normalize import normalize_country_code
from .models import (
    InstrumentCategory, TradingInstrument,
    SignalStatValue, ContractWeight, SignalWeight
)
from .models.MarketSession import MarketSession
from .models.extremes import Rolling52WeekStats
from .models.target_high_low import TargetHighLowConfig
from .models.vwap import VwapMinute
from .models.Market24h import MarketTrading24Hour
from .models.MarketIntraDay import MarketIntraday
from .models.Instrument_Intraday import InstrumentIntraday


class ColumnSetFilter(admin.SimpleListFilter):
    title = "Column set"
    parameter_name = "colset"

    def lookups(self, request, model_admin):
        return (
            ("basic", "Basic"),
            ("price", "Price / Live"),
            ("targets", "Entry & Targets"),
            ("session", "Session & Range"),
            ("backtest", "Backtest Stats"),
            ("full", "Everything (wide)"),
        )

    def queryset(self, request, queryset):
        # Column set selection only influences list display
        return queryset


class SignalStatValueInline(admin.TabularInline):
    model = SignalStatValue
    extra = 0
    fields = ['signal', 'value']


class ContractWeightInline(admin.StackedInline):
    model = ContractWeight
    extra = 0
    fields = ['weight']


class MarketSessionCountryFilter(admin.SimpleListFilter):
    """Normalize country choices so alias rows collapse to canonical options."""

    title = "By country"
    parameter_name = "country"

    def lookups(self, request, model_admin):
        queryset = model_admin.get_queryset(request)
        seen = set()
        options = []

        def add_option(raw_country: str):
            canonical = normalize_country_code(raw_country)
            if not canonical or canonical in seen:
                return
            seen.add(canonical)
            options.append((canonical, self._label(canonical)))

        for country in get_control_countries(require_session_capture=True):
            add_option(country)

        dynamic_countries = queryset.order_by().values_list('country', flat=True).distinct()
        for raw in dynamic_countries:
            add_option(raw)

        return options

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        variants = self._variants(value)
        if not variants:
            return queryset.none()
        return queryset.filter(country__in=variants)

    def _variants(self, raw_country: str) -> set[str]:
        canonical = normalize_country_code(raw_country)
        if not canonical:
            return set()

        variants = {canonical, raw_country}
        toggled = []
        if "_" in canonical:
            toggled.append(canonical.replace("_", "-"))
        if "-" in canonical:
            toggled.append(canonical.replace("-", "_"))

        for value in list(variants) + toggled:
            variants.update({value, value.upper(), value.lower(), value.title()})
            if "_" in value:
                variants.add(value.replace("_", "-"))
            if "-" in value:
                variants.add(value.replace("-", "_"))

        return {entry for entry in variants if entry}

    def _label(self, canonical: str) -> str:
        if canonical == "Pre_USA":
            return "Pre-USA"
        return canonical


@admin.register(InstrumentCategory)
class InstrumentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'is_active', 'sort_order']
    list_filter = ['is_active']
    list_editable = ['is_active', 'sort_order']
    search_fields = ['name', 'display_name']


@admin.register(TradingInstrument)
class TradingInstrumentAdmin(admin.ModelAdmin):
    list_display = [
        'symbol', 'name', 'category', 'exchange', 'tick_value', 'margin_requirement', 
        'is_active', 'is_watchlist', 'show_in_ribbon'
    ]
    list_filter = ['category', 'is_active', 'is_watchlist', 'show_in_ribbon', 'exchange']
    list_editable = ['is_active', 'is_watchlist', 'show_in_ribbon']
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
            'fields': ('is_active', 'is_watchlist', 'show_in_ribbon', 'sort_order')
        }),
        ('Display Configuration', {
            'fields': ('display_precision', 'tick_size', 'contract_size')
        }),
        ('Trading Calculations', {
            'fields': ('tick_value', 'margin_requirement')
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
    change_list_template = "admin/ThorTrading/marketsession/change_list.html"
    # Preset column bundles for the change list view
    COLUMN_SETS = {
        "basic": (
            "captured_at",
            "country",
            "symbol",
            "bhs",
            "wndw",
            "day",
        ),
        "price": (
            "captured_at",
            "country",
            "symbol",
            "last_price",
            "change",
            "change_percent",
            "bid_price",
            "bid_size",
            "ask_price",
            "ask_size",
            "volume",
            "spread",
        ),
        "targets": (
            "captured_at",
            "country",
            "symbol",
            "bhs",
            "entry_price",
            "target_high",
            "target_low",
            "target_hit_price",
            "target_hit_type",
            "target_hit_at",
        ),
        "session": (
            "captured_at",
            "country",
            "symbol",
            "open_price_24h",
            "prev_close_24h",
            "open_prev_diff_24h",
            "open_prev_pct_24h",
            "low_24h",
            "high_24h",
            "range_diff_24h",
            "range_pct_24h",
            "low_52w",
            "low_pct_52w",
            "high_52w",
            "high_pct_52w",
            "range_52w",
            "range_pct_52w",
        ),
        "backtest": (
            "captured_at",
            "country",
            "symbol",
            "bhs",
            "country_symbol_wndw_total",
            "strong_buy_worked", "strong_buy_worked_percentage",
            "strong_buy_didnt_work", "strong_buy_didnt_work_percentage",
            "buy_worked", "buy_worked_percentage",
            "buy_didnt_work", "buy_didnt_work_percentage",
            "hold",
            "strong_sell_worked", "strong_sell_worked_percentage",
            "strong_sell_didnt_work", "strong_sell_didnt_work_percentage",
            "sell_worked", "sell_worked_percentage",
            "sell_didnt_work", "sell_didnt_work_percentage",
            "weighted_average",
            "instrument_count",
        ),
        "full": (
            "captured_at",
            "country",
            "symbol",
            "bhs",
            "wndw",
            "session_number",
            "country_symbol",
            "year",
            "month",
            "date",
            "day",
            "weight",
            "weighted_average",
            "instrument_count",
            "entry_price",
            "last_price",
            "target_high",
            "target_low",
            "target_hit_price",
            "target_hit_type",
            "market_open",
            "market_high_open",
            "market_high_pct_open",
            "market_low_open",
            "market_low_pct_open",
            "market_close",
            "market_high_pct_close",
            "market_low_pct_close",
            "market_close_vs_open_pct",
            "market_range",
            "market_range_pct",
            "prev_close_24h",
            "open_price_24h",
            "open_prev_diff_24h",
            "open_prev_pct_24h",
            "low_24h",
            "high_24h",
            "range_diff_24h",
            "range_pct_24h",
            "low_52w",
            "low_pct_52w",
            "high_52w",
            "high_pct_52w",
            "range_52w",
            "range_pct_52w",
            "volume",
            "bid_price",
            "bid_size",
            "ask_price",
            "ask_size",
            "spread",
            "strong_buy_worked", "strong_buy_worked_percentage",
            "strong_buy_didnt_work", "strong_buy_didnt_work_percentage",
            "buy_worked", "buy_worked_percentage",
            "buy_didnt_work", "buy_didnt_work_percentage",
            "hold",
            "strong_sell_worked", "strong_sell_worked_percentage",
            "strong_sell_didnt_work", "strong_sell_didnt_work_percentage",
            "sell_worked", "sell_worked_percentage",
            "sell_didnt_work", "sell_didnt_work_percentage",
        ),
    }

    # Default to the full column set so admin loads all fields by default.
    DEFAULT_COLUMN_SET = "full"
    list_display = COLUMN_SETS[DEFAULT_COLUMN_SET]

    def get_list_display(self, request):
        colset = request.GET.get("colset", self.DEFAULT_COLUMN_SET)
        return self.COLUMN_SETS.get(colset, self.COLUMN_SETS[self.DEFAULT_COLUMN_SET])

    list_filter = [
        ColumnSetFilter,
        MarketSessionCountryFilter,
        'symbol',
        'day',
        'bhs',
        'wndw',  # filter by Worked / Didn't Work / Neutral labels
        'year',
        'month',
        'date',
    ]
    search_fields = ['country', 'session_number', 'symbol']
    readonly_fields = ['captured_at']
    
    fieldsets = (
        ('Session Info', {
            'fields': ('session_number', 'country', 'symbol', 'country_symbol', 'year', 'month', 'date', 'day', 'captured_at')
        }),
        ('Live Price Data (Open)', {
            'fields': ('last_price', 'ask_price', 'ask_size',
                      'bid_price', 'bid_size', 'volume', 'spread')
        }),
        ('Session Price Data', {
            'fields': ('prev_close_24h', 'open_price_24h', 'open_prev_diff_24h', 'open_prev_pct_24h')
        }),
        ('Range Data', {
            'fields': (
                'low_24h', 'high_24h', 'range_diff_24h', 'range_pct_24h',
                'low_52w', 'low_pct_52w', 'high_52w', 'high_pct_52w', 'range_52w', 'range_pct_52w'
            ),
            'classes': ('collapse',)
        }),
        ('Entry & Targets', {
            'fields': ('entry_price', 'target_high', 'target_low')
        }),
        ('Signal & Composite', {
            'fields': (
                    'bhs', 'country_symbol_wndw_total',
                'strong_buy_worked', 'strong_buy_worked_percentage',
                'strong_buy_didnt_work', 'strong_buy_didnt_work_percentage',
                'buy_worked', 'buy_worked_percentage', 'buy_didnt_work', 'buy_didnt_work_percentage',
                'hold',
                'strong_sell_worked', 'strong_sell_worked_percentage',
                'strong_sell_didnt_work', 'strong_sell_didnt_work_percentage',
                    'sell_worked', 'sell_worked_percentage',
                    'sell_didnt_work', 'sell_didnt_work_percentage',
                        'weighted_average', 'weight',
                            'instrument_count')
        }),
    )
    
    def date_display(self, obj):
        return f"{obj.year}/{obj.month:02d}/{obj.date:02d}"
    date_display.short_description = 'Date'
    
    ordering = ['-session_number', 'symbol']

    class Media:
        css = {
            'all': ('ThorTrading/admin/marketsession.css',)
        }
        js = ('ThorTrading/admin/marketsession.js',)


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
        'stale_hours_display',
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

    def get_readonly_fields(self, request, obj=None):
        ro = ['last_price_checked', 'last_updated', 'created_at']
        if obj and not request.user.is_superuser:
            ro.extend([
                'high_52w', 'high_52w_date', 'low_52w', 'low_52w_date',
                'all_time_high', 'all_time_high_date', 'all_time_low', 'all_time_low_date'
            ])
        return ro

    def stale_hours_display(self, obj):
        val = obj.stale_hours()
        return f"{val:.2f}" if val is not None else '-'
    stale_hours_display.short_description = 'Stale (h)'


# Target High / Low Configuration Admin


@admin.register(TargetHighLowConfig)
class TargetHighLowConfigAdmin(admin.ModelAdmin):
    list_display = [
        'symbol', 'mode', 'offset_high', 'offset_low', 'percent_high', 'percent_low', 'is_active', 'updated_at'
    ]
    list_filter = ['mode', 'is_active']
    search_fields = ['symbol']
    list_editable = ['mode', 'offset_high', 'offset_low', 'percent_high', 'percent_low', 'is_active']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['symbol']

    fieldsets = (
        ('Symbol & Mode', {
            'fields': ('symbol', 'mode', 'is_active'),
            'description': 'Select POINTS, PERCENT or DISABLED. Disabled skips target computation.'
        }),
        ('Point Offsets', {
            'fields': ('offset_high', 'offset_low'),
            'description': 'Required when mode=POINTS (absolute values).'
        }),
        ('Percent Offsets', {
            'fields': ('percent_high', 'percent_low'),
            'description': 'Required when mode=PERCENT (e.g. 0.50 = +0.50%).'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(VwapMinute)
class VwapMinuteAdmin(admin.ModelAdmin):
    list_display = ("symbol", "timestamp_minute", "last_price", "cumulative_volume", "captured_at")
    list_filter = ("symbol",)
    search_fields = ("symbol",)
    ordering = ("-timestamp_minute", "symbol")


@admin.register(MarketTrading24Hour)
class MarketTrading24HourAdmin(admin.ModelAdmin):
    list_display = (
        "session_group", "session_date", "country", "symbol",
        "open_price_24h", "prev_close_24h", "low_24h", "high_24h",
        "range_diff_24h", "range_pct_24h", "close_24h", "finalized",
    )
    list_filter = (
        "session_date", "country", "symbol", "finalized",
    )
    search_fields = (
        "symbol", "country", "session_group",
    )
    ordering = ("-session_date", "symbol")
    date_hierarchy = "session_date"
    readonly_fields = ("finalized",)


@admin.register(MarketIntraday)
class MarketIntradayAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp_minute", "country", "symbol",
        "open_1m", "high_1m", "low_1m", "close_1m", "volume_1m",
    )
    list_filter = (
        "country", "symbol",
    )
    search_fields = (
        "symbol", "country",
    )
    ordering = ("-timestamp_minute", "symbol")
    date_hierarchy = "timestamp_minute"
    readonly_fields = ("timestamp_minute",)


@admin.register(InstrumentIntraday)
class InstrumentIntradayAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp_minute", "symbol",
        "open_1m", "high_1m", "low_1m", "close_1m", "volume_1m",
        "bid_last", "ask_last", "spread_last",
    )
    list_filter = ("symbol",)
    search_fields = ("symbol",)
    ordering = ("-timestamp_minute", "symbol")
    date_hierarchy = "timestamp_minute"
    readonly_fields = ("timestamp_minute",)




