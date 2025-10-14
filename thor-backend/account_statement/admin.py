"""
Admin configuration for Account Statement app.

Registers admin interfaces for paper accounts, real accounts, and account summaries.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import PaperAccount, RealAccount, AccountSummary, BrokerageProvider


@admin.register(PaperAccount)
class PaperAccountAdmin(admin.ModelAdmin):
    """
    Admin interface for paper trading accounts.
    """
    
    list_display = (
        'user', 'account_number', 'net_liquidating_value', 
        'starting_balance', 'reset_count', 'status', 'created_at'
    )
    list_filter = ('status', 'base_currency', 'created_at', 'reset_count')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'account_number')
    readonly_fields = ('account_number', 'created_at', 'updated_at', 'last_reset_date')
    
    fieldsets = (
        ('Account Information', {
            'fields': ('user', 'account_number', 'status', 'base_currency')
        }),
        ('Balances', {
            'fields': (
                'starting_balance', 'current_balance', 'net_liquidating_value',
                'stock_buying_power', 'option_buying_power', 'available_funds_for_trading'
            )
        }),
        ('Positions', {
            'fields': (
                'long_stock_value', 'long_marginable_value', 'short_marginable_value',
                'margin_equity', 'equity_percentage', 'maintenance_requirement'
            ),
            'classes': ('collapse',)
        }),
        ('Fees & Commissions', {
            'fields': (
                'equity_commissions_fees_ytd', 'option_commissions_fees_ytd',
                'futures_commissions_fees_ytd', 'total_commissions_fees_ytd'
            ),
            'classes': ('collapse',)
        }),
        ('Paper Account Specific', {
            'fields': ('reset_count', 'last_reset_date')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'last_statement_date'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['reset_selected_accounts']
    
    def reset_selected_accounts(self, request, queryset):
        """Reset selected paper accounts to starting balance."""
        count = 0
        for account in queryset:
            account.reset_account()
            count += 1
        
        self.message_user(request, f'{count} paper accounts reset successfully.')
    reset_selected_accounts.short_description = "Reset selected paper accounts"
    
    def get_readonly_fields(self, request, obj=None):
        """Make calculated fields readonly."""
        readonly = list(self.readonly_fields)
        if obj:  # Editing existing object
            readonly.extend(['net_liquidating_value', 'total_commissions_fees_ytd'])
        return readonly


@admin.register(RealAccount)
class RealAccountAdmin(admin.ModelAdmin):
    """
    Admin interface for real money trading accounts.
    """
    
    list_display = (
        'user', 'account_nickname', 'brokerage_provider', 'net_liquidating_value',
        'is_verified', 'api_enabled', 'status', 'created_at'
    )
    list_filter = (
        'brokerage_provider', 'is_verified', 'api_enabled', 'status',
        'day_trading_enabled', 'margin_enabled', 'created_at'
    )
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name', 
        'account_number', 'account_nickname', 'external_account_id'
    )
    readonly_fields = (
        'account_number', 'created_at', 'updated_at', 'verification_date',
        'last_sync_date', 'sync_errors'
    )
    
    fieldsets = (
        ('Account Information', {
            'fields': (
                'user', 'brokerage_provider', 'account_nickname', 
                'account_number', 'external_account_id', 'status', 'base_currency'
            )
        }),
        ('Verification & API', {
            'fields': (
                'is_verified', 'verification_date', 'api_enabled',
                'last_sync_date', 'sync_errors'
            )
        }),
        ('Trading Permissions', {
            'fields': (
                'day_trading_enabled', 'margin_enabled', 'options_level'
            )
        }),
        ('Risk Management', {
            'fields': ('daily_loss_limit', 'position_size_limit')
        }),
        ('Balances', {
            'fields': (
                'current_balance', 'net_liquidating_value',
                'stock_buying_power', 'option_buying_power', 'available_funds_for_trading'
            )
        }),
        ('Positions', {
            'fields': (
                'long_stock_value', 'long_marginable_value', 'short_marginable_value',
                'margin_equity', 'equity_percentage', 'maintenance_requirement',
                'money_market_balance'
            ),
            'classes': ('collapse',)
        }),
        ('Fees & Commissions', {
            'fields': (
                'equity_commissions_fees_ytd', 'option_commissions_fees_ytd',
                'futures_commissions_fees_ytd', 'total_commissions_fees_ytd'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'last_statement_date'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['sync_selected_accounts', 'verify_selected_accounts']
    
    def sync_selected_accounts(self, request, queryset):
        """Sync selected real accounts with brokerage APIs."""
        count = 0
        errors = 0
        
        for account in queryset.filter(api_enabled=True):
            try:
                account.sync_with_brokerage()
                count += 1
            except Exception:
                errors += 1
        
        if count > 0:
            self.message_user(request, f'{count} accounts synced successfully.')
        if errors > 0:
            self.message_user(request, f'{errors} accounts failed to sync.', level='WARNING')
    sync_selected_accounts.short_description = "Sync selected real accounts"
    
    def verify_selected_accounts(self, request, queryset):
        """Mark selected accounts as verified (admin override)."""
        from django.utils import timezone
        count = queryset.filter(is_verified=False).update(
            is_verified=True,
            verification_date=timezone.now()
        )
        self.message_user(request, f'{count} accounts marked as verified.')
    verify_selected_accounts.short_description = "Mark selected accounts as verified"
    
    def get_readonly_fields(self, request, obj=None):
        """Make calculated fields readonly."""
        readonly = list(self.readonly_fields)
        if obj:  # Editing existing object
            readonly.extend(['net_liquidating_value', 'total_commissions_fees_ytd'])
        return readonly


@admin.register(AccountSummary)
class AccountSummaryAdmin(admin.ModelAdmin):
    """
    Admin interface for account summaries.
    """
    
    list_display = (
        'get_account_info', 'statement_date', 'pnl_day', 'pnl_ytd', 
        'pnl_percent', 'net_liquidating_value_snapshot', 'created_at'
    )
    list_filter = ('statement_date', 'created_at', 'content_type')
    search_fields = ('object_id',)  # This isn't ideal but works for now
    readonly_fields = ('created_at', 'pnl_percent')
    
    fieldsets = (
        ('Account Reference', {
            'fields': ('content_type', 'object_id')
        }),
        ('Summary Information', {
            'fields': ('statement_date', 'net_liquidating_value_snapshot', 'mark_value')
        }),
        ('P&L Tracking', {
            'fields': ('pnl_open', 'pnl_day', 'pnl_ytd', 'pnl_percent')
        }),
        ('Risk Metrics', {
            'fields': ('margin_requirement',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_account_info(self, obj):
        """Display account information in list view."""
        if obj.account:
            return f"{obj.account.user.email} - {obj.account.__class__.__name__}"
        return "N/A"
    get_account_info.short_description = "Account"
    get_account_info.admin_order_field = 'object_id'
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related('content_type')


# Custom admin site configuration
admin.site.site_header = "Thor Trading Platform Administration"
admin.site.site_title = "Thor Admin"
admin.site.index_title = "Welcome to Thor Trading Platform Administration"
