"""Expose the ThorTrading URL patterns under the api namespace."""
from ThorTrading.urls import app_name, urlpatterns

__all__ = ["app_name", "urlpatterns"]
