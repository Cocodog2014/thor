"""
Consumer App Validation and Registration System

This module provides mechanisms to validate that consumer apps are real,
authorized, and capable of receiving data before allowing them in the pipeline.
"""

from __future__ import annotations

import uuid
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)


class AppValidationStatus(models.TextChoices):
    """Status of consumer app validation."""
    PENDING = "pending", "Pending Validation"
    VERIFIED = "verified", "Verified Active"
    FAILED = "failed", "Validation Failed"
    SUSPENDED = "suspended", "Suspended"
    REVOKED = "revoked", "Access Revoked"


class AppCapability(models.TextChoices):
    """Data capabilities that apps can request."""
    QUOTES_LIVE = "quotes_live", "Live Quotes"
    QUOTES_HISTORICAL = "quotes_historical", "Historical Quotes"
    FUTURES_DATA = "futures_data", "Futures Market Data"
    OPTIONS_DATA = "options_data", "Options Market Data"
    LEVEL_1 = "level_1", "Level 1 Market Data"
    LEVEL_2 = "level_2", "Level 2 Market Data"


@dataclass(frozen=True)
class ValidationResult:
    """Result of app validation check."""
    is_valid: bool
    status: AppValidationStatus
    message: str
    capabilities: List[str]
    last_verified: Optional[datetime] = None
    next_check: Optional[datetime] = None


class ConsumerAppValidation(models.Model):
    """Extended validation and security for consumer apps."""
    
    consumer_app = models.OneToOneField(
        'SchwabLiveData.ConsumerApp',
        on_delete=models.CASCADE,
        related_name='validation'
    )
    
    # Registration & Identity
    api_key = models.CharField(
        max_length=64, 
        unique=True,
        help_text="Unique API key for this consumer app"
    )
    
    secret_hash = models.CharField(
        max_length=128,
        help_text="Hashed secret for signature validation"
    )
    
    # App Configuration
    callback_url = models.URLField(
        blank=True,
        help_text="Health check/heartbeat endpoint for this app"
    )
    
    expected_schema_version = models.CharField(
        max_length=16,
        default="1.0",
        help_text="Expected data schema version this app can handle"
    )
    
    capabilities = models.JSONField(
        default=list,
        help_text="List of data capabilities this app is authorized for"
    )
    
    # Validation Status
    validation_status = models.CharField(
        max_length=20,
        choices=AppValidationStatus.choices,
        default=AppValidationStatus.PENDING
    )
    
    last_validated = models.DateTimeField(null=True, blank=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    
    validation_failures = models.PositiveIntegerField(default=0)
    max_failures = models.PositiveIntegerField(default=3)
    
    # Usage Tracking
    last_data_request = models.DateTimeField(null=True, blank=True)
    total_requests = models.PositiveIntegerField(default=0)
    
    # Metadata
    registration_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Consumer App Validation"
        verbose_name_plural = "Consumer App Validations"
    
    def __str__(self):
        return f"{self.consumer_app.code} - {self.validation_status}"
    
    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = self.generate_api_key()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a unique API key for the consumer app."""
        return f"thor_{uuid.uuid4().hex[:24]}"
    
    def set_secret(self, secret: str) -> None:
        """Set and hash the app secret."""
        self.secret_hash = hashlib.sha256(
            f"{self.api_key}:{secret}".encode()
        ).hexdigest()
    
    def verify_signature(self, data: str, signature: str) -> bool:
        """Verify HMAC signature from the consumer app."""
        if not self.secret_hash:
            return False
        
        expected = hmac.new(
            self.secret_hash.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
    
    def is_authorized_for(self, capability: str) -> bool:
        """Check if app is authorized for a specific capability."""
        return (
            self.validation_status == AppValidationStatus.VERIFIED and
            capability in self.capabilities
        )
    
    def record_heartbeat(self) -> None:
        """Record that the app is alive and responding."""
        self.last_heartbeat = timezone.now()
        self.save(update_fields=['last_heartbeat'])
    
    def record_request(self) -> None:
        """Record a data request from this app."""
        self.last_data_request = timezone.now()
        self.total_requests += 1
        self.save(update_fields=['last_data_request', 'total_requests'])
    
    async def validate_app_connectivity(self) -> ValidationResult:
        """Validate that the app is reachable and responding correctly."""
        if not self.callback_url:
            return ValidationResult(
                is_valid=False,
                status=AppValidationStatus.FAILED,
                message="No callback URL configured for validation",
                capabilities=[]
            )
        
        try:
            # Create validation challenge
            challenge = uuid.uuid4().hex
            timestamp = int(timezone.now().timestamp())
            
            # Expected response signature
            expected_response = hmac.new(
                self.secret_hash.encode(),
                f"{challenge}:{timestamp}".encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Send validation request
            response = requests.post(
                f"{self.callback_url}/validate",
                json={
                    "challenge": challenge,
                    "timestamp": timestamp,
                    "api_key": self.api_key
                },
                timeout=10
            )
            
            if response.status_code != 200:
                self.validation_failures += 1
                return ValidationResult(
                    is_valid=False,
                    status=AppValidationStatus.FAILED,
                    message=f"Validation endpoint returned {response.status_code}",
                    capabilities=[]
                )
            
            data = response.json()
            
            # Verify response signature
            if not self.verify_signature(
                f"{challenge}:{timestamp}",
                data.get("signature", "")
            ):
                self.validation_failures += 1
                return ValidationResult(
                    is_valid=False,
                    status=AppValidationStatus.FAILED,
                    message="Invalid signature in validation response",
                    capabilities=[]
                )
            
            # App is valid
            self.validation_status = AppValidationStatus.VERIFIED
            self.last_validated = timezone.now()
            self.validation_failures = 0
            self.save()
            
            return ValidationResult(
                is_valid=True,
                status=AppValidationStatus.VERIFIED,
                message="App validation successful",
                capabilities=self.capabilities,
                last_verified=self.last_validated,
                next_check=self.last_validated + timedelta(hours=24)
            )
            
        except requests.RequestException as e:
            self.validation_failures += 1
            logger.warning(f"App validation failed for {self.consumer_app.code}: {e}")
            
            # Suspend if too many failures
            if self.validation_failures >= self.max_failures:
                self.validation_status = AppValidationStatus.SUSPENDED
            
            self.save()
            
            return ValidationResult(
                is_valid=False,
                status=AppValidationStatus.FAILED,
                message=f"Connection failed: {str(e)}",
                capabilities=[]
            )
    
    @property
    def is_active(self) -> bool:
        """Check if app is active and validated."""
        return (
            self.consumer_app.is_active and
            self.validation_status == AppValidationStatus.VERIFIED and
            self.validation_failures < self.max_failures
        )
    
    @property
    def needs_validation(self) -> bool:
        """Check if app needs re-validation."""
        if not self.last_validated:
            return True
        
        # Re-validate daily for active apps
        return (
            timezone.now() - self.last_validated > timedelta(hours=24)
        )


class AppRegistrationRequest(models.Model):
    """Temporary model for handling app registration requests."""
    
    app_name = models.CharField(max_length=128)
    app_code = models.SlugField(max_length=64)
    description = models.TextField()
    callback_url = models.URLField()
    requested_capabilities = models.JSONField(default=list)
    
    # Contact info
    developer_name = models.CharField(max_length=128)
    developer_email = models.EmailField()
    organization = models.CharField(max_length=128, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    
    def approve(self, reviewer):
        """Approve this registration and create the consumer app."""
        from .models import ConsumerApp
        
        # Create the consumer app
        consumer_app = ConsumerApp.objects.create(
            code=self.app_code,
            display_name=self.app_name,
            description=self.description,
            is_active=True
        )
        
        # Create validation record
        validation = ConsumerAppValidation.objects.create(
            consumer_app=consumer_app,
            callback_url=self.callback_url,
            capabilities=self.requested_capabilities,
            validation_status=AppValidationStatus.PENDING,
            registration_notes=f"Approved by {reviewer.username}"
        )
        
        # Generate secret
        secret = uuid.uuid4().hex
        validation.set_secret(secret)
        validation.save()
        
        # Update request status
        self.status = 'approved'
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.save()
        
        return consumer_app