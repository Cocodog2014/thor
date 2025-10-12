from django.contrib import admin
from django.contrib import messages
from django import forms

from .models import ConsumerApp, DataFeed
from .thor_apps import get_available_apps


class ConsumerAppForm(forms.ModelForm):
	"""Custom form for ConsumerApp with dropdown of real Thor apps."""
	
	code = forms.ChoiceField(
		choices=[],  # Will be populated in __init__
		help_text="Select from actual Thor project applications only"
	)
	
	class Meta:
		model = ConsumerApp
		fields = '__all__'
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# Populate choices with real Thor apps
		self.fields['code'].choices = [('', '--- Select a Thor Application ---')] + get_available_apps()
		
		# If editing an existing app, make code field read-only
		if self.instance and self.instance.pk:
			self.fields['code'].widget.attrs['readonly'] = True
			self.fields['code'].help_text = "App code cannot be changed after creation"


@admin.register(DataFeed)
class DataFeedAdmin(admin.ModelAdmin):
	list_display = ("display_name", "code", "connection_type", "provider_key", "is_active", "updated_at")
	list_filter = ("connection_type", "provider_key", "is_active")
	search_fields = ("display_name", "code", "description")
	ordering = ("display_name",)
	readonly_fields = ("created_at", "updated_at")


# Simplified ConsumerApp admin - no more complex FeedAssignment inline
@admin.register(ConsumerApp)
class ConsumerAppAdmin(admin.ModelAdmin):
	form = ConsumerAppForm
	list_display = ("display_name", "code", "primary_feed", "fallback_feed", "is_active")
	list_filter = ("is_active", "primary_feed", "fallback_feed")
	search_fields = ("display_name", "code", "description")
	ordering = ("display_name",)
	readonly_fields = ("created_at", "updated_at", "authorized_capabilities")
	
	fieldsets = (
		(None, {
			'fields': ('code', 'display_name', 'description', 'is_active')
		}),
		('Data Sources', {
			'fields': ('primary_feed', 'fallback_feed'),
			'description': 'Select which data feeds this app should use'
		}),
		('Auto-Configured', {
			'fields': ('authorized_capabilities',),
			'classes': ('collapse',),
			'description': 'These fields are automatically set based on the app type'
		}),
		('Timestamps', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		})
	)
	
	def save_model(self, request, obj, form, change):
		"""Override save to show helpful messages."""
		try:
			super().save_model(request, obj, form, change)
			
			action = "Updated" if change else "Created"
			messages.success(
				request, 
				f"✅ {action} '{obj.display_name}' → Primary: {obj.primary_feed}"
			)
			
			if obj.fallback_feed:
				messages.info(
					request,
					f"📡 Fallback configured: {obj.fallback_feed}"
				)
		except Exception as e:
			messages.error(request, f"❌ Error: {str(e)}")


# Remove FeedAssignment admin - no longer needed
# @admin.register(FeedAssignment)


## Note: Cloudflared admin control is exposed via a custom admin view in
## SchwabLiveData.admin_views and wired under /admin/cloudflared/ in urls.py.

