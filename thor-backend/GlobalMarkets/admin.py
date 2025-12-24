from django import forms
from django.contrib import admin
from .models import Market, USMarketStatus, UserMarketWatchlist, MarketDataSnapshot


DAY_CHOICES = [
    (0, "Monday"),
    (1, "Tuesday"),
    (2, "Wednesday"),
    (3, "Thursday"),
    (4, "Friday"),
    (5, "Saturday"),
    (6, "Sunday"),
]


class MarketAdminForm(forms.ModelForm):
    trading_days = forms.MultipleChoiceField(
        choices=DAY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Days to track this market. Leave blank to track all days.",
    )

    class Meta:
        model = Market
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["trading_days"] = [str(d) for d in (self.instance.trading_days or [])]

    def clean_trading_days(self):
        vals = self.cleaned_data.get("trading_days") or []
        return sorted({int(v) for v in vals})


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    form = MarketAdminForm
    list_display = [
        'country', 'timezone_name', 'market_open_time', 'market_close_time',
        'status', 'is_active', 'currency',
        'enable_session_capture',
        'enable_open_capture',
        'enable_close_capture',
        'live_status',
    ]
    list_filter = ['status', 'is_active', 'currency', 'enable_session_capture', 'enable_open_capture', 'enable_close_capture']
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
        ('Trading Days', {
            'fields': ('trading_days',),
            'description': 'Select days to track this market. Blank = all days.'
        }),
        ('Status', {
            'fields': ('status', 'is_active')
        }),
        ('Session Capture', {
            'fields': (
                'enable_session_capture',
                'enable_open_capture',
                'enable_close_capture',
            ),
            'description': 'Control if this market writes rows into ThorTrading.MarketSession.'
        }),
    )

    @admin.display(description='Live Status')
    def live_status(self, obj):
        # NOTE: This calls runtime logic per row; if admin gets slow,
        # consider caching or storing "computed live status" elsewhere.
        if obj.status == "OPEN":
            if obj.is_market_open_now():
                return "🟢 TRADING"
            return "🟡 OPEN (After Hours)"
        return "🔴 CLOSED"


@admin.register(USMarketStatus)
class TradingCalendarAdmin(admin.ModelAdmin):
    list_display = ['exchange_code', 'date', 'is_trading_day', 'holiday_name', 'created_at']
    list_filter = ['exchange_code', 'is_trading_day', 'date']
    search_fields = ['holiday_name', 'exchange_code']
    ordering = ['exchange_code', '-date']
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
    list_select_related = ("user", "market")


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
    list_select_related = ("market",)

    def has_add_permission(self, request):
        # Snapshots should only be created programmatically
        return False

    # Uncomment if you want snapshots to be immutable in admin:
    # def has_change_permission(self, request, obj=None):
    #     return False
    #
    # def has_delete_permission(self, request, obj=None):
    #     return False

