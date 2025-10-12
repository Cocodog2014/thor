"""
Simple Consumer App Validation Service

This provides basic validation to detect and prevent fake consumer app registrations.
"""

from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from datetime import timedelta
import requests
import logging

logger = logging.getLogger(__name__)


class ConsumerValidationError(Exception):
    """Base exception for consumer validation issues."""
    pass


def validate_consumer_app(consumer_app, capability="quotes_live"):
    """
    Validate that a consumer app is authorized for data access.
    
    Args:
        consumer_app: ConsumerApp instance
        capability: Required capability (e.g., 'quotes_live')
        
    Raises:
        ConsumerValidationError: If validation fails
    """
    
    # Check if app is active
    if not consumer_app.is_active:
        raise ConsumerValidationError(f"Consumer app '{consumer_app.code}' is inactive")
    
    # Check if app is validated (prevents fake apps)
    if not consumer_app.is_validated:
        logger.warning(f"FAKE APP DETECTED: Unvalidated app '{consumer_app.code}' attempted data access")
        raise ConsumerValidationError(
            f"Consumer app '{consumer_app.code}' is not validated. "
            "This may be a fake app created without proper registration."
        )
    
    # Check validation failures
    if consumer_app.validation_failures >= 3:
        raise ConsumerValidationError(f"Consumer app '{consumer_app.code}' has too many validation failures")
    
    # Check capability authorization
    if capability not in consumer_app.authorized_capabilities:
        logger.warning(f"Unauthorized capability request: {consumer_app.code} -> {capability}")
        raise ConsumerValidationError(
            f"Consumer app '{consumer_app.code}' is not authorized for '{capability}'"
        )
    
    logger.info(f"✅ Validated access: {consumer_app.code} -> {capability}")


def test_app_connectivity(consumer_app):
    """
    Test if a consumer app is reachable via its callback URL.
    
    Returns:
        bool: True if app responds correctly
    """
    if not consumer_app.callback_url:
        return False
    
    try:
        # Simple ping to health endpoint
        response = requests.get(
            f"{consumer_app.callback_url}/health",
            timeout=5,
            headers={
                'User-Agent': 'Thor-DataPipeline/1.0',
                'X-API-Key': consumer_app.api_key
            }
        )
        
        if response.status_code == 200:
            # Update validation status
            consumer_app.last_validated = timezone.now()
            consumer_app.validation_failures = 0
            consumer_app.save(update_fields=['last_validated', 'validation_failures'])
            return True
        else:
            consumer_app.validation_failures += 1
            consumer_app.save(update_fields=['validation_failures'])
            return False
            
    except requests.RequestException as e:
        logger.warning(f"Connectivity test failed for {consumer_app.code}: {e}")
        consumer_app.validation_failures += 1
        consumer_app.save(update_fields=['validation_failures'])
        return False


def audit_fake_apps():
    """
    Audit the system for fake/unvalidated consumer apps.
    
    Returns:
        dict: Audit results
    """
    from .models import ConsumerApp
    
    all_apps = ConsumerApp.objects.all()
    fake_apps = all_apps.filter(is_validated=False)
    failed_apps = all_apps.filter(validation_failures__gte=3)
    
    return {
        'total_apps': all_apps.count(),
        'validated_apps': all_apps.filter(is_validated=True).count(),
        'fake_apps': fake_apps.count(),
        'failed_apps': failed_apps.count(),
        'fake_app_list': [
            {
                'code': app.code,
                'display_name': app.display_name,
                'is_active': app.is_active,
                'has_feed_assignments': app.assignments.exists(),
                'security_status': app.security_status
            }
            for app in fake_apps
        ]
    }


def cleanup_fake_apps(dry_run=True):
    """
    Clean up fake/invalid consumer apps.
    
    Args:
        dry_run: If True, just report what would be done
        
    Returns:
        dict: Cleanup results
    """
    from .models import ConsumerApp
    
    actions = []
    
    # Find unvalidated apps
    fake_apps = ConsumerApp.objects.filter(is_validated=False, is_active=True)
    
    for app in fake_apps:
        action = f"Would deactivate fake app: {app.code}"
        if not dry_run:
            app.is_active = False
            app.save()
            action = f"✅ Deactivated fake app: {app.code}"
        actions.append(action)
    
    # Find apps with too many failures
    failed_apps = ConsumerApp.objects.filter(validation_failures__gte=3, is_active=True)
    
    for app in failed_apps:
        action = f"Would deactivate failed app: {app.code}"
        if not dry_run:
            app.is_active = False
            app.save()
            action = f"✅ Deactivated failed app: {app.code}"
        actions.append(action)
    
    return {
        'dry_run': dry_run,
        'actions': actions
    }