"""
Registry of actual applications in the Thor project.

This defines the real apps that can consume market data, preventing
fake apps from being registered through the admin interface.
"""

from typing import Dict, List, Tuple


# Define your actual Thor project applications
THOR_APPLICATIONS = {
    'futures_trading': {
        'display_name': 'Futures Trading App',
        'description': 'Main futures trading interface and signals',
        'capabilities': ['quotes_live', 'futures_data', 'level_1'],
        'module_path': 'FutureTrading',
        'is_active': True,
    },
    'stock_trading': {
        'display_name': 'Stock Trading App', 
        'description': 'Stock and options trading interface',
        'capabilities': ['quotes_live', 'stock_data', 'options_data', 'level_1'],
        'module_path': 'StockTrading',
        'is_active': True,
    },
    'thor_frontend': {
        'display_name': 'Thor React Frontend',
        'description': 'Main React.js frontend dashboard',
        'capabilities': ['quotes_live', 'futures_data', 'stock_data'],
        'module_path': 'thor-frontend',
        'is_active': True,
    },
    'thor_api': {
        'display_name': 'Thor API Backend',
        'description': 'Django REST API backend',
        'capabilities': ['quotes_live', 'futures_data', 'stock_data', 'level_1', 'level_2'],
        'module_path': 'api',
        'is_active': True,
    },
    # Add more real apps as your project grows
}


def get_available_apps() -> List[Tuple[str, str]]:
    """
    Get list of available apps for Django choice field.
    
    Returns:
        List of (code, display_name) tuples for use in Django forms
    """
    return [
        (code, app_info['display_name'])
        for code, app_info in THOR_APPLICATIONS.items()
        if app_info['is_active']
    ]


def get_app_info(app_code: str) -> Dict:
    """Get information about a specific app."""
    return THOR_APPLICATIONS.get(app_code, {})


def is_valid_app(app_code: str) -> bool:
    """Check if an app code is valid and active."""
    app_info = THOR_APPLICATIONS.get(app_code)
    return app_info is not None and app_info.get('is_active', False)


def get_app_capabilities(app_code: str) -> List[str]:
    """Get the capabilities for a specific app."""
    app_info = THOR_APPLICATIONS.get(app_code, {})
    return app_info.get('capabilities', [])