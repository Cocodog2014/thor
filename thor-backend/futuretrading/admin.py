from django.contrib import admin
from .models import (
    InstrumentCategory, TradingInstrument,
    WatchlistGroup, WatchlistItem,
    SignalStatValue, ContractWeight, SignalWeight
)


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


@admin.register(WatchlistGroup)
class WatchlistGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'sort_order', 'is_active']
    list_editable = ['sort_order', 'is_active']
    search_fields = ['name']


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    list_display = ['group', 'instrument', 'sort_order', 'is_active']
    list_filter = ['group', 'is_active']
    list_editable = ['sort_order', 'is_active']
    search_fields = ['instrument__symbol', 'group__name']
