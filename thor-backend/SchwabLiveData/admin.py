from django.contrib import admin

from .models import ConsumerApp, DataFeed, FeedAssignment


@admin.register(DataFeed)
class DataFeedAdmin(admin.ModelAdmin):
	list_display = ("display_name", "code", "connection_type", "provider_key", "is_active", "updated_at")
	list_filter = ("connection_type", "provider_key", "is_active")
	search_fields = ("display_name", "code", "description")
	ordering = ("display_name",)
	readonly_fields = ("created_at", "updated_at")


class FeedAssignmentInline(admin.TabularInline):
	model = FeedAssignment
	extra = 1
	autocomplete_fields = ("feed",)
	fields = ("feed", "is_primary", "is_enabled", "priority", "notes")
	readonly_fields = ("created_at", "updated_at")


@admin.register(ConsumerApp)
class ConsumerAppAdmin(admin.ModelAdmin):
	list_display = ("display_name", "code", "is_active", "default_feed")
	list_filter = ("is_active",)
	search_fields = ("display_name", "code", "description")
	ordering = ("display_name",)
	readonly_fields = ("created_at", "updated_at")
	inlines = (FeedAssignmentInline,)


@admin.register(FeedAssignment)
class FeedAssignmentAdmin(admin.ModelAdmin):
	list_display = (
		"consumer_app",
		"feed",
		"is_primary",
		"is_enabled",
		"priority",
		"updated_at",
	)
	list_filter = ("is_primary", "is_enabled", "consumer_app__code", "feed__code")
	search_fields = (
		"consumer_app__display_name",
		"consumer_app__code",
		"feed__display_name",
		"feed__code",
		"notes",
	)
	ordering = ("consumer_app__display_name", "priority")
	autocomplete_fields = ("consumer_app", "feed")
	readonly_fields = ("created_at", "updated_at")
