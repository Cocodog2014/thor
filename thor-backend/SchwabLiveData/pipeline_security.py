"""
Data Pipeline Security and Validation Service

This service enforces that only validated, authenticated consumer apps
can receive market data through the pipeline.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from django.db.models import Q, F

from .models import ConsumerApp, DataFeed
from .app_validation import ConsumerAppValidation, AppValidationStatus, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class SecurityContext:
    """Security context for data requests."""
    consumer_code: str
    api_key: Optional[str] = None
    signature: Optional[str] = None
    timestamp: Optional[int] = None
    requested_capabilities: List[str] = None


class PipelineSecurityError(Exception):
    """Base exception for pipeline security violations."""
    pass


class UnauthorizedConsumerError(PipelineSecurityError):
    """Consumer app is not authorized for this operation."""
    pass


class InvalidSignatureError(PipelineSecurityError):
    """Request signature is invalid."""
    pass


class UnregisteredAppError(PipelineSecurityError):
    """Consumer app is not properly registered."""
    pass


class DataPipelineValidator:
    """Validates and secures the data pipeline."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def validate_consumer_access(
        self, 
        consumer_code: str, 
        requested_capability: str = "quotes_live",
        security_context: Optional[SecurityContext] = None
    ) -> Tuple[ConsumerApp, ConsumerAppValidation]:
        """
        Validate that a consumer app is authorized to access data.
        
        Args:
            consumer_code: The consumer app identifier
            requested_capability: The data capability being requested
            security_context: Optional security context with API key/signature
            
        Returns:
            Tuple of (ConsumerApp, ConsumerAppValidation)
            
        Raises:
            UnregisteredAppError: If the app is not registered
            UnauthorizedConsumerError: If the app is not authorized
            InvalidSignatureError: If the signature is invalid
        """
        
        # 1. Check if consumer app exists
        try:
            consumer_app = ConsumerApp.objects.get(code__iexact=consumer_code)
        except ConsumerApp.DoesNotExist:
            self.logger.warning(f"Unregistered app attempted access: {consumer_code}")
            raise UnregisteredAppError(f"Consumer app '{consumer_code}' is not registered")
        
        # 2. Check if app is active
        if not consumer_app.is_active:
            self.logger.warning(f"Inactive app attempted access: {consumer_code}")
            raise UnauthorizedConsumerError(f"Consumer app '{consumer_code}' is inactive")
        
        # 3. Check if validation record exists
        try:
            validation = consumer_app.validation
        except ConsumerAppValidation.DoesNotExist:
            self.logger.error(f"App missing validation record: {consumer_code}")
            raise UnregisteredAppError(f"Consumer app '{consumer_code}' lacks validation record")
        
        # 4. Check validation status
        if validation.validation_status != AppValidationStatus.VERIFIED:
            self.logger.warning(f"Unverified app attempted access: {consumer_code} (status: {validation.validation_status})")
            raise UnauthorizedConsumerError(f"Consumer app '{consumer_code}' is not verified")
        
        # 5. Check capability authorization
        if not validation.is_authorized_for(requested_capability):
            self.logger.warning(f"Unauthorized capability request: {consumer_code} -> {requested_capability}")
            raise UnauthorizedConsumerError(
                f"Consumer app '{consumer_code}' is not authorized for '{requested_capability}'"
            )
        
        # 6. Validate signature if provided
        if security_context and security_context.api_key:
            if not self._validate_signature(validation, security_context):
                raise InvalidSignatureError("Invalid request signature")
        
        # 7. Record the access
        validation.record_request()
        
        self.logger.info(f"Authorized access: {consumer_code} -> {requested_capability}")
        return consumer_app, validation
    
    def _validate_signature(
        self, 
        validation: ConsumerAppValidation, 
        context: SecurityContext
    ) -> bool:
        """Validate the request signature."""
        
        if not context.signature or not context.timestamp:
            return False
        
        # Check API key matches
        if context.api_key != validation.api_key:
            self.logger.warning(f"API key mismatch for {validation.consumer_app.code}")
            return False
        
        # Check timestamp freshness (within 5 minutes)
        request_time = datetime.fromtimestamp(context.timestamp, tz=timezone.utc)
        age = timezone.now() - request_time
        if age > timedelta(minutes=5):
            self.logger.warning(f"Stale request from {validation.consumer_app.code}: {age}")
            return False
        
        # Verify signature
        data = f"{context.consumer_code}:{context.timestamp}"
        return validation.verify_signature(data, context.signature)
    
    def get_authorized_feeds(self, consumer_code: str) -> List[Dict[str, Any]]:
        """Get list of feeds this consumer is authorized to access."""
        
        consumer_app, validation = self.validate_consumer_access(consumer_code)
        
        feeds = []
        
        # Add primary feed if exists and active
        if consumer_app.primary_feed and consumer_app.primary_feed.is_active:
            feeds.append({
                'code': consumer_app.primary_feed.code,
                'display_name': consumer_app.primary_feed.display_name,
                'connection_type': consumer_app.primary_feed.connection_type,
                'provider_key': consumer_app.primary_feed.provider_key,
                'is_primary': True,
                'priority': 1
            })
        
        # Add fallback feed if exists, active, and different from primary
        if (consumer_app.fallback_feed and 
            consumer_app.fallback_feed.is_active and 
            consumer_app.fallback_feed != consumer_app.primary_feed):
            feeds.append({
                'code': consumer_app.fallback_feed.code,
                'display_name': consumer_app.fallback_feed.display_name,
                'connection_type': consumer_app.fallback_feed.connection_type,
                'provider_key': consumer_app.fallback_feed.provider_key,
                'is_primary': False,
                'priority': 2
            })
        
        return feeds
    
    def audit_consumer_access(self, hours: int = 24) -> Dict[str, Any]:
        """Audit consumer access patterns."""
        
        since = timezone.now() - timedelta(hours=hours)
        
        # Get all validations with recent activity
        recent_validations = ConsumerAppValidation.objects.filter(
            Q(last_data_request__gte=since) | Q(last_heartbeat__gte=since)
        ).select_related('consumer_app')
        
        audit_data = {
            'period_hours': hours,
            'total_active_apps': recent_validations.count(),
            'apps': []
        }
        
        for validation in recent_validations:
            app_data = {
                'code': validation.consumer_app.code,
                'display_name': validation.consumer_app.display_name,
                'status': validation.validation_status,
                'total_requests': validation.total_requests,
                'last_request': validation.last_data_request,
                'last_heartbeat': validation.last_heartbeat,
                'capabilities': validation.capabilities,
                'validation_failures': validation.validation_failures
            }
            audit_data['apps'].append(app_data)
        
        return audit_data
    
    def cleanup_invalid_apps(self, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up invalid or stale consumer apps."""
        
        results = {
            'dry_run': dry_run,
            'actions': []
        }
        
        # Find apps without validation records
        apps_without_validation = ConsumerApp.objects.filter(
            validation__isnull=True
        )
        
        for app in apps_without_validation:
            action = f"Would deactivate unvalidated app: {app.code}"
            if not dry_run:
                app.is_active = False
                app.save()
                action = f"Deactivated unvalidated app: {app.code}"
            results['actions'].append(action)
        
        # Find apps with too many failures
        failed_validations = ConsumerAppValidation.objects.filter(
            validation_failures__gte=F('max_failures')
        )
        
        for validation in failed_validations:
            action = f"Would suspend failed app: {validation.consumer_app.code}"
            if not dry_run:
                validation.validation_status = AppValidationStatus.SUSPENDED
                validation.save()
                action = f"Suspended failed app: {validation.consumer_app.code}"
            results['actions'].append(action)
        
        # Find stale apps (no activity in 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        stale_validations = ConsumerAppValidation.objects.filter(
            Q(last_data_request__lt=thirty_days_ago) | Q(last_data_request__isnull=True),
            Q(last_heartbeat__lt=thirty_days_ago) | Q(last_heartbeat__isnull=True),
            validation_status=AppValidationStatus.VERIFIED
        )
        
        for validation in stale_validations:
            action = f"Would mark stale app for review: {validation.consumer_app.code}"
            if not dry_run:
                validation.validation_status = AppValidationStatus.PENDING
                validation.save()
                action = f"Marked stale app for review: {validation.consumer_app.code}"
            results['actions'].append(action)
        
        return results


# Global validator instance
pipeline_validator = DataPipelineValidator()


def require_validated_consumer(capability: str = "quotes_live"):
    """Decorator to require validated consumer for API endpoints."""
    
    def decorator(view_func):
        def wrapper(self, request, *args, **kwargs):
            consumer_code = request.GET.get('consumer') or request.data.get('consumer')
            
            if not consumer_code:
                raise ValidationError("Missing 'consumer' parameter")
            
            # Extract security context
            security_context = SecurityContext(
                consumer_code=consumer_code,
                api_key=request.headers.get('X-API-Key'),
                signature=request.headers.get('X-Signature'),
                timestamp=request.headers.get('X-Timestamp')
            )
            
            try:
                consumer_app, validation = pipeline_validator.validate_consumer_access(
                    consumer_code=consumer_code,
                    requested_capability=capability,
                    security_context=security_context
                )
                
                # Add to request context
                request.validated_consumer = consumer_app
                request.consumer_validation = validation
                
                return view_func(self, request, *args, **kwargs)
                
            except PipelineSecurityError as e:
                raise PermissionDenied(str(e))
        
        return wrapper
    return decorator