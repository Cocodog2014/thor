from __future__ import annotations

from django.db import models
from django.core.exceptions import ValidationError
import uuid
import hashlib


class DataFeed(models.Model):
	"""Represents an upstream data source such as Excel RTD or Schwab API."""

	code = models.SlugField(max_length=64, unique=True)
	display_name = models.CharField(max_length=128)
	description = models.TextField(blank=True)
	connection_type = models.CharField(
		max_length=64,
		default="internal",
		help_text="Logical connector type, e.g. excel_rtd, schwab_api, websocket",
	)
	provider_key = models.CharField(
		max_length=64,
		blank=True,
		help_text="Identifier used by provider_factory to instantiate the backend connector.",
	)
	is_active = models.BooleanField(default=True)
	metadata = models.JSONField(blank=True, default=dict)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ("display_name",)

	def __str__(self) -> str:  # pragma: no cover - trivial
		return f"{self.display_name} ({self.code})"


class ConsumerApp(models.Model):
	"""Front-end or downstream service that consumes normalized market data."""

	code = models.SlugField(
		max_length=64, 
		unique=True,
		help_text="Must be one of the predefined Thor applications"
	)
	display_name = models.CharField(max_length=128)
	description = models.TextField(blank=True)
	is_active = models.BooleanField(default=True)
	
	# Auto-populated from thor_apps.py registry
	authorized_capabilities = models.JSONField(
		default=list,
		help_text="Auto-populated based on app registry"
	)
	
	# Direct feed selection (simplified - no more FeedAssignment)
	primary_feed = models.ForeignKey(
		"DataFeed",
		null=True,  # Temporarily allow null for migration
		blank=True,
		on_delete=models.PROTECT,
		related_name="primary_consumers",
		help_text="Primary data feed for this consumer app"
	)
	fallback_feed = models.ForeignKey(
		"DataFeed",
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="fallback_consumers",
		help_text="Fallback feed if primary fails"
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ("display_name",)

	def __str__(self) -> str:  # pragma: no cover - trivial
		return f"{self.display_name} ({self.code})"
	
	def clean(self):
		"""Validate that the app code is a real Thor application."""
		from .thor_apps import is_valid_app, get_app_info
		
		if not is_valid_app(self.code):
			raise ValidationError({
				'code': f"'{self.code}' is not a valid Thor application. "
						"Choose from the predefined applications only."
			})
		
		# Prevent primary and fallback being the same
		if self.primary_feed and self.fallback_feed and self.primary_feed == self.fallback_feed:
			raise ValidationError({
				'fallback_feed': "Fallback feed cannot be the same as primary feed"
			})
		
		# Auto-populate fields from registry
		app_info = get_app_info(self.code)
		if app_info:
			if not self.display_name:
				self.display_name = app_info['display_name']
			if not self.description:
				self.description = app_info['description']
			self.authorized_capabilities = app_info['capabilities']
	
	def save(self, *args, **kwargs):
		self.full_clean()  # This calls clean() to validate
		super().save(*args, **kwargs)
	
	@property
	def is_real_app(self) -> bool:
		"""All apps in this system are real (validated by clean method)."""
		from .thor_apps import is_valid_app
		return self.is_active and is_valid_app(self.code)
	
	@property
	def app_module_path(self) -> str:
		"""Get the module path for this app."""
		from .thor_apps import get_app_info
		app_info = get_app_info(self.code)
		return app_info.get('module_path', '')
	
	@property 
	def current_provider(self) -> str:
		"""Get the current provider key for this consumer."""
		if self.primary_feed and self.primary_feed.is_active:
			return self.primary_feed.provider_key
		elif self.fallback_feed and self.fallback_feed.is_active:
			return self.fallback_feed.provider_key
		else:
			return "excel_live"  # Default fallback


# FeedAssignment model removed - no longer needed with simplified approach
