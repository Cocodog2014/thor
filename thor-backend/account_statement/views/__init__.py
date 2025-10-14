"""
Account Statement views package.

This package contains separate view modules for paper and real trading accounts,
along with shared base views and utilities.
"""

from .base import *
from .paper import *
from .real import *

# Export commonly used views
__all__ = [
    # Base views
    'AccountListView',
    'AccountDetailView', 
    'AccountSummaryListView',
    
    # Paper account views
    'PaperAccountListView',
    'PaperAccountDetailView',
    'PaperAccountCreateView',
    'PaperAccountResetView',
    
    # Real account views
    'RealAccountListView',
    'RealAccountDetailView',
    'RealAccountCreateView',
    'RealAccountSyncView',
]