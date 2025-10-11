"""Custom template context processors for the Thor project."""

from django.conf import settings

def frontend_base_url(_request):
    """Expose the configured frontend base URL to templates."""
    return {'FRONTEND_BASE_URL': settings.FRONTEND_BASE_URL}
