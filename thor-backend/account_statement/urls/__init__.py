"""
Account Statement URLs package.

This package contains separate URL modules for paper and real trading accounts,
along with shared base URLs.
"""

from .base import urlpatterns, app_name

# Export for Django URL discovery
__all__ = [
    'urlpatterns',
    'app_name',
]