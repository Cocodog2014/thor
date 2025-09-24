from django.contrib import admin
from .models import Market, USMarketStatus, UserMarketWatchlist, MarketDataSnapshot


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = [
        'country', 'timezone_name', 'market_open_time', 'market_close_time', 
        'status', 'is_active', 'currency', 'get_market_status_display'
    ]
    list_filter = ['status', 'is_active', 'currency']
    search_fields = ['country', 'timezone_name']
    ordering = ['country']
    list_per_page = 25
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('country', 'timezone_name', 'currency')
        }),
        ('Trading Hours', {
            'fields': ('market_open_time', 'market_close_time')
        }),
        ('Status', {
            'fields': ('status', 'is_active')
        }),
    )
    
    def get_market_status_display(self, obj):
        if obj.status == "OPEN":
            if obj.is_market_open_now():
                return "🟢 TRADING"
            else:
                return "� OPEN (After Hours)"
        else:
            return "🔴 CLOSED"
    get_market_status_display.short_description = 'Live Status'


@admin.register(USMarketStatus)
class USMarketStatusAdmin(admin.ModelAdmin):
    list_display = ['date', 'is_trading_day', 'holiday_name', 'created_at']
    list_filter = ['is_trading_day', 'date']
    search_fields = ['holiday_name']
    ordering = ['-date']
    date_hierarchy = 'date'
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return ['date']
        return []


@admin.register(UserMarketWatchlist)
class UserMarketWatchlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'market', 'display_name', 'is_primary', 'order']
    list_filter = ['is_primary', 'market__country']
    search_fields = ['user__username', 'market__country', 'display_name']
    ordering = ['user', 'order']


@admin.register(MarketDataSnapshot)
class MarketDataSnapshotAdmin(admin.ModelAdmin):
    list_display = [
        'market', 'market_status', 'collected_at', 'market_time', 
        'dst_active', 'is_in_trading_hours'
    ]
    list_filter = [
        'market_status', 'dst_active', 'is_in_trading_hours', 
        'market__country', 'collected_at'
    ]
    search_fields = ['market__country']
    ordering = ['-collected_at']
    date_hierarchy = 'collected_at'
    readonly_fields = ['collected_at']
    
    def has_add_permission(self, request):
        # Snapshots should only be created programmatically
        return False