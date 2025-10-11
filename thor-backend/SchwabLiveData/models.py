from __future__ import annotations

from django.db import models


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

	code = models.SlugField(max_length=64, unique=True)
	display_name = models.CharField(max_length=128)
	description = models.TextField(blank=True)
	is_active = models.BooleanField(default=True)
	default_feed = models.ForeignKey(
		"DataFeed",
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="default_for_apps",
		help_text="Fallback feed when no explicit assignment is active.",
	)
	feeds = models.ManyToManyField(
		"DataFeed",
		through="FeedAssignment",
		related_name="consumer_apps",
		blank=True,
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ("display_name",)

	def __str__(self) -> str:  # pragma: no cover - trivial
		return f"{self.display_name} ({self.code})"


class FeedAssignment(models.Model):
	"""Mapping between feeds and consumer apps with routing preferences."""

	consumer_app = models.ForeignKey(
		ConsumerApp,
		on_delete=models.CASCADE,
		related_name="assignments",
	)
	feed = models.ForeignKey(
		DataFeed,
		on_delete=models.CASCADE,
		related_name="assignments",
	)
	is_primary = models.BooleanField(
		default=False,
		help_text="If selected, use this feed before others when multiple are enabled.",
	)
	is_enabled = models.BooleanField(
		default=True,
		help_text="Toggle to enable/disable this feed for the consumer without deleting the link.",
	)
	priority = models.PositiveIntegerField(
		default=100,
		help_text="Lower numbers are preferred when multiple feeds are enabled.",
	)
	notes = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = ("consumer_app", "feed")
		ordering = ("priority", "-is_primary", "feed__display_name")

	def __str__(self) -> str:  # pragma: no cover - trivial
		status = "primary" if self.is_primary else "secondary"
		return f"{self.consumer_app.code} ↔ {self.feed.code} ({status})"

	@property
	def is_active(self) -> bool:
		"""Convenience flag to determine if the assignment should be used."""

		return self.is_enabled and self.feed.is_active and self.consumer_app.is_active
