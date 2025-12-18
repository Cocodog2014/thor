"""
Users app models for Thor trading platform.

This app provides identity & access management with a CustomUser model
that extends Django's AbstractUser with trading-specific fields.
"""

from typing import TYPE_CHECKING, Optional

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone

if TYPE_CHECKING:
    from LiveData.schwab.models import BrokerConnection


class CustomUserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        # Set username to email if not provided
        if not extra_fields.get('username'):
            extra_fields['username'] = email
            
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.OWNER)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class UserRole(models.TextChoices):
    """User role definitions for the Thor trading platform."""
    OWNER = 'OWNER', 'Owner'
    ADMIN = 'ADMIN', 'Administrator'
    TRADER = 'TRADER', 'Trader'
    VIEWER = 'VIEWER', 'Viewer'


class CustomUser(AbstractUser):
    """
    Custom user model for Thor trading platform.
    
    Extends Django's AbstractUser with trading-specific fields:
    - email as unique identifier (can be used for login)
    - optional username for display purposes
    - trading-specific metadata
    - timezone support for market hours
    - MFA support for security
    - role-based access control
    """
    
    # Email as primary identifier (unique)
    email = models.EmailField(
        unique=True,
        help_text="Required. Used for login and notifications."
    )
    
    # Username is optional (kept for compatibility)
    username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Optional. Display name for the platform."
    )
    
    # Additional user fields
    display_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Public display name shown in the interface"
    )
    
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text="User's preferred timezone for market hours display"
    )
    
    phone = models.CharField(
        max_length=17,  # +1-555-555-5555 format
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ],
        help_text="Phone number for MFA and notifications"
    )
    
    mfa_enabled = models.BooleanField(
        default=False,
        help_text="Whether multi-factor authentication is enabled"
    )
    
    role = models.CharField(
        max_length=10,
        choices=UserRole.choices,
        default=UserRole.TRADER,
        help_text="User's role in the trading platform"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="IP address of last login"
    )
    
    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']  # Required when creating superuser
    
    # Use custom manager
    objects = CustomUserManager()
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        """String representation of the user."""
        if self.display_name:
            return f"{self.display_name} ({self.email})"
        elif self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name} ({self.email})"
        else:
            return self.email
    
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        if self.display_name:
            return self.display_name
        full_name = f'{self.first_name} {self.last_name}'
        return full_name.strip() or self.email
    
    def get_short_name(self):
        """Return the short name for the user."""
        if self.display_name:
            return self.display_name
        return self.first_name or self.email.split('@')[0]
    
    def is_owner(self):
        """Check if user has owner privileges."""
        return self.role == UserRole.OWNER
    
    def is_admin(self):
        """Check if user has admin privileges."""
        return self.role in [UserRole.OWNER, UserRole.ADMIN]
    
    def is_trader(self):
        """Check if user has trading privileges."""
        return self.role in [UserRole.OWNER, UserRole.ADMIN, UserRole.TRADER]
    
    def can_view_accounts(self):
        """Check if user can view account data."""
        return True  # All users can view their own accounts
    
    def can_trade(self):
        """Check if user can execute trades."""
        return self.is_trader()
    
    def can_manage_users(self):
        """Check if user can manage other users."""
        return self.is_admin()
    
    # Broker connection helpers -------------------------------------------------
    def get_broker_connection(self, broker: str) -> Optional["BrokerConnection"]:
        """Return the first broker connection for the provided broker code."""

        manager = getattr(self, "broker_connections", None)
        if manager is None:
            return None
        return manager.filter(broker=broker).first()

    @property
    def schwab_token(self):
        """Backward-compatible accessor for Schwab broker connection."""
        return self.get_broker_connection("SCHWAB")

    def get_active_schwab_token(self):
        """Return Schwab broker connection when present and not expired."""
        token = self.get_broker_connection("SCHWAB")
        if not token:
            return None
        if getattr(token, "is_expired", False):
            return None
        return token

    def save(self, *args, **kwargs):
        """Override save to set display_name if not provided."""
        if not self.display_name and (self.first_name or self.last_name):
            self.display_name = f"{self.first_name} {self.last_name}".strip()
        
        # Ensure username is set to email if not provided
        if not self.username:
            self.username = self.email
        
        super().save(*args, **kwargs)
