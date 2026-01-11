"""
Admin configuration for Users app.
"""

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import CustomUser, UserRole


class ApprovalStatusFilter(SimpleListFilter):
    title = "Approval"
    parameter_name = "approval"

    def lookups(self, request, model_admin):
        return (
            ("pending", "New / Pending approval"),
            ("approved", "Approved"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "pending":
            return queryset.filter(is_approved=False)
        if value == "approved":
            return queryset.filter(is_approved=True)
        return queryset


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """
    Custom admin for the CustomUser model.
    
    Extends Django's default UserAdmin with additional fields
    and better organization for trading platform users.
    """
    
    # Lists
    list_display = (
        'email', 'display_name', 'role', 'is_active', 
        'is_approved', 'mfa_enabled', 'last_login', 'created_at'
    )
    list_editable = ('is_approved',)
    list_filter = (
        'role', 'is_active', 'is_staff', ApprovalStatusFilter, 'mfa_enabled', 'created_at'
    )
    search_fields = ('email', 'first_name', 'last_name', 'display_name')
    ordering = ('-created_at',)
    
    # Form organization
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'password', 'username')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'display_name', 'phone')
        }),
        ('Trading Settings', {
            'fields': ('role', 'timezone', 'mfa_enabled')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_approved', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('last_login', 'last_login_ip', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Required Information', {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name'),
        }),
        ('Trading Settings', {
            'classes': ('wide',),
            'fields': ('role', 'timezone'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'last_login_ip')
    
    # Custom methods for display
    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related()
    
    def save_model(self, request, obj, form, change):
        """Custom save logic for admin."""
        if not change:  # Creating new user
            # Set default display_name if not provided
            if not obj.display_name and (obj.first_name or obj.last_name):
                obj.display_name = f"{obj.first_name} {obj.last_name}".strip()
        
        super().save_model(request, obj, form, change)
    
    # Custom admin actions
    actions = ['approve_users', 'unapprove_users', 'enable_mfa', 'disable_mfa', 'set_trader_role', 'set_viewer_role']

    def approve_users(self, request, queryset):
        count = queryset.update(is_approved=True)
        self.message_user(request, f'Approved {count} users.')
    approve_users.short_description = "Approve selected users"

    def unapprove_users(self, request, queryset):
        count = queryset.update(is_approved=False)
        self.message_user(request, f'Unapproved {count} users.')
    unapprove_users.short_description = "Mark selected users as unapproved"
    
    def enable_mfa(self, request, queryset):
        """Enable MFA for selected users."""
        count = queryset.update(mfa_enabled=True)
        self.message_user(request, f'MFA enabled for {count} users.')
    enable_mfa.short_description = "Enable MFA for selected users"
    
    def disable_mfa(self, request, queryset):
        """Disable MFA for selected users."""
        count = queryset.update(mfa_enabled=False)
        self.message_user(request, f'MFA disabled for {count} users.')
    disable_mfa.short_description = "Disable MFA for selected users"
    
    def set_trader_role(self, request, queryset):
        """Set role to TRADER for selected users."""
        count = queryset.update(role=UserRole.TRADER)
        self.message_user(request, f'Role set to TRADER for {count} users.')
    set_trader_role.short_description = "Set role to TRADER"
    
    def set_viewer_role(self, request, queryset):
        """Set role to VIEWER for selected users."""
        count = queryset.update(role=UserRole.VIEWER)
        self.message_user(request, f'Role set to VIEWER for {count} users.')
    set_viewer_role.short_description = "Set role to VIEWER"
