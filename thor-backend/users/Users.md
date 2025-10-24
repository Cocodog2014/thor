# Users App Documentation

## Overview

The Users app provides comprehensive identity and access management for the Thor trading platform. It implements a custom user model extending Django's `AbstractUser` with trading-specific functionality, role-based permissions, and enhanced security features including multi-factor authentication support.

## Architecture

### Custom User Model Design

The app replaces Django's default User model with a `CustomUser` model that serves as the foundation for all user management in the platform:

```
users/
├── models.py           # CustomUser model with trading-specific fields
├── admin.py            # Enhanced admin interface for user management
├── apps.py             # App configuration
├── views.py            # User management views (future development)
└── migrations/         # Database migrations
```

## Models

### UserRole (TextChoices)

Defines the role hierarchy for the trading platform:

- **OWNER** - Full platform access, can manage everything
- **ADMIN** - Administrative access, can manage users and system settings  
- **TRADER** - Trading access, can execute trades and manage accounts
- **VIEWER** - Read-only access, can view data but not trade

### CustomUser Model

Extends Django's `AbstractUser` with trading platform-specific functionality.

#### Authentication Fields
- `email` (EmailField, unique) - Primary login identifier
- `username` (CharField, optional) - Display name, auto-set to email if blank
- `password` - Inherited from AbstractUser

#### Personal Information
- `first_name` - Inherited from AbstractUser
- `last_name` - Inherited from AbstractUser  
- `display_name` (CharField) - Public display name shown in interface
- `phone` (CharField) - Phone number for MFA and notifications
  - Regex validation: `^\+?1?\d{9,15}$`
  - Format: +1-555-555-5555

#### Trading Platform Settings
- `role` (CharField) - User role from UserRole choices, default: TRADER
- `timezone` (CharField) - User's preferred timezone, default: UTC
- `mfa_enabled` (BooleanField) - Multi-factor authentication status

#### Security & Tracking
- `is_active` - Inherited from AbstractUser
- `is_staff` - Inherited from AbstractUser
- `is_superuser` - Inherited from AbstractUser
- `last_login` - Inherited from AbstractUser
- `last_login_ip` (GenericIPAddressField) - IP address of last login
- `created_at` (DateTimeField) - Account creation timestamp
- `updated_at` (DateTimeField) - Last profile update

#### Authentication Configuration
- `USERNAME_FIELD = 'email'` - Use email for login instead of username
- `REQUIRED_FIELDS = ['first_name', 'last_name']` - Required for superuser creation

## Model Methods

### Display Methods
- `__str__()` - Returns display_name(email) or first_name last_name(email)
- `get_full_name()` - Returns display_name or "first_name last_name"
- `get_short_name()` - Returns display_name or first_name or email prefix

### Permission Methods
- `is_owner()` - Check if user has owner privileges
- `is_admin()` - Check if user has admin privileges (OWNER or ADMIN)
- `is_trader()` - Check if user has trading privileges (OWNER, ADMIN, or TRADER)
- `can_view_accounts()` - Check if user can view account data (always True)
- `can_trade()` - Check if user can execute trades
- `can_manage_users()` - Check if user can manage other users

### Automatic Field Management
- Auto-sets `display_name` from first/last name if not provided
- Auto-sets `username` to email if not provided
- Maintains `updated_at` timestamp on save

## Admin Interface

### CustomUserAdmin

Comprehensive admin interface extending Django's `UserAdmin`:

#### List View
- **Display Fields:** email, display_name, role, is_active, mfa_enabled, last_login, created_at
- **Filters:** role, is_active, is_staff, mfa_enabled, created_at
- **Search:** email, first_name, last_name, display_name
- **Ordering:** -created_at (newest first)

#### Form Organization
**Authentication Section:**
- email, password, username

**Personal Info Section:**
- first_name, last_name, display_name, phone

**Trading Settings Section:**
- role, timezone, mfa_enabled

**Permissions Section (Collapsible):**
- is_active, is_staff, is_superuser, groups, user_permissions

**Metadata Section (Collapsible):**
- last_login, last_login_ip, created_at, updated_at

#### Create User Form
**Required Information:**
- email, password1, password2, first_name, last_name

**Trading Settings:**
- role, timezone

#### Admin Actions
- **Enable MFA** - Bulk enable MFA for selected users
- **Disable MFA** - Bulk disable MFA for selected users  
- **Set Trader Role** - Bulk set role to TRADER
- **Set Viewer Role** - Bulk set role to VIEWER

#### Custom Logic
- Auto-sets display_name on user creation if not provided
- Optimized queryset with select_related for performance
- Helpful success messages for bulk actions

## Role-Based Access Control

### Permission Hierarchy
```
OWNER (Full Access)
├── Can manage all users
├── Can access all accounts
├── Can modify system settings
└── Can execute all trading operations

ADMIN (Administrative Access)  
├── Can manage users (except owners)
├── Can access user accounts
├── Can modify platform settings
└── Can execute trading operations

TRADER (Trading Access)
├── Can manage own accounts only
├── Can execute trading operations
├── Cannot manage other users
└── Cannot modify system settings

VIEWER (Read-Only Access)
├── Can view own accounts only
├── Cannot execute trades
├── Cannot manage users
└── Cannot modify settings
```

### Permission Methods Usage
```python
# Check trading permissions
if user.can_trade():
    # Allow trade execution
    pass

# Check admin access
if user.can_manage_users():
    # Show user management interface
    pass

# Check account access (always True for own accounts)
if user.can_view_accounts():
    # Show account dashboard
    pass
```

## Email-Based Authentication

### Login Configuration
- Users log in with email address instead of username
- Username field is optional and used only for display
- Email field has unique constraint enforced at database level

### User Creation Process
1. Email address required and validated for uniqueness
2. Password meets Django's validation requirements
3. First name and last name required for admin-created users
4. Role defaults to TRADER for new users
5. Display name auto-generated if not provided

## Security Features

### Multi-Factor Authentication Support
- `mfa_enabled` flag tracks MFA status
- Admin interface allows bulk MFA management
- Phone number field supports MFA delivery
- Framework ready for MFA implementation

### IP Tracking
- `last_login_ip` tracks user login locations
- Useful for security monitoring and suspicious activity detection
- Admin interface displays this information

### Field Validation
- Email format validation with uniqueness constraint
- Phone number regex validation
- Role restricted to defined choices
- Password validation inherited from Django

## Integration Points

### Account Statement Integration
- CustomUser serves as AUTH_USER_MODEL for the platform
- Foreign key relationships from account models
- Role-based access control for account management
- User ownership enforcement in views and APIs

### Future Trading App Integration
- Role permissions control trading capabilities
- User preferences (timezone) affect market hour displays
- MFA requirements for high-value trades
- Audit trail with user identification

## Settings Configuration

### AUTH_USER_MODEL Setting
```python
# In settings.py
AUTH_USER_MODEL = 'users.CustomUser'
```

### App Registration
```python
INSTALLED_APPS = [
    # ... other apps
    'users',  # Custom user management with identity & access
    # ... more apps
]
```

## Database Schema

### CustomUser Table Fields
```sql
-- Core authentication
email VARCHAR(254) UNIQUE NOT NULL
username VARCHAR(150) NULL
password VARCHAR(128) NOT NULL

-- Personal information  
first_name VARCHAR(150)
last_name VARCHAR(150)
display_name VARCHAR(100)
phone VARCHAR(17)

-- Platform settings
role VARCHAR(10) DEFAULT 'TRADER'
timezone VARCHAR(50) DEFAULT 'UTC'
mfa_enabled BOOLEAN DEFAULT FALSE

-- Django user fields
is_active BOOLEAN DEFAULT TRUE
is_staff BOOLEAN DEFAULT FALSE  
is_superuser BOOLEAN DEFAULT FALSE
date_joined TIMESTAMP
last_login TIMESTAMP

-- Custom tracking
last_login_ip INET NULL
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

### Indexes
- Unique index on email field
- Index on role for filtering
- Index on is_active for active user queries
- Index on created_at for chronological sorting

## API Considerations

### Future API Endpoints
- `GET /api/users/me/` - Get current user profile
- `PUT /api/users/me/` - Update current user profile
- `POST /api/users/me/change-password/` - Change password
- `POST /api/users/me/enable-mfa/` - Enable MFA
- `POST /api/users/me/disable-mfa/` - Disable MFA

### Admin API Endpoints (Admin/Owner only)
- `GET /api/users/` - List all users
- `POST /api/users/` - Create new user
- `GET /api/users/{id}/` - Get user details
- `PUT /api/users/{id}/` - Update user
- `DELETE /api/users/{id}/` - Deactivate user

## Migration Strategy

### Initial Migration
Since this changes the AUTH_USER_MODEL, it must be done before any other apps are migrated:

1. Add users app to INSTALLED_APPS
2. Set AUTH_USER_MODEL = 'users.CustomUser'
3. Run initial migration: `python manage.py makemigrations users`
4. Run migration: `python manage.py migrate users`
5. Migrate other apps that reference User model

### Data Migration (if needed)
If migrating from existing Django User model:
1. Create data migration to copy user data
2. Update foreign key references
3. Drop old user table
4. Update application code

## Testing Strategy

### Unit Tests
- Model validation and field constraints
- Permission method functionality
- Display name auto-generation
- Email uniqueness enforcement

### Integration Tests
- Admin interface functionality
- User creation and update flows
- Role-based permission enforcement
- Authentication with email

### Security Tests
- Email uniqueness validation
- Password strength requirements
- MFA flag functionality
- IP tracking accuracy

## Performance Considerations

### Database Optimization
- Efficient indexes on frequently queried fields
- Select_related in admin queries
- Proper field sizing for performance

### Admin Interface
- Pagination for large user lists
- Optimized search queries
- Bulk action efficiency

## Security Best Practices

### Data Protection
- Email addresses treated as PII
- Phone numbers encrypted at rest (future enhancement)
- IP addresses logged but not exposed to non-admins
- Password hashing with Django defaults

### Access Control
- Role-based permissions enforced at model level
- Admin actions restricted by user permissions
- Audit trail for user management operations

## Development Guidelines

### Code Standards
- Follow Django best practices for custom user models
- Comprehensive docstrings for all methods
- Type hints where appropriate
- Consistent naming conventions

### Future Enhancements

#### Planned Features
- Email verification workflow
- Password reset functionality
- MFA implementation (TOTP/SMS)
- User profile pictures
- Account lockout after failed attempts
- Advanced audit logging

#### Advanced Security
- Login attempt monitoring
- Suspicious activity detection
- Session management
- Device registration
- Compliance reporting

#### User Experience
- User preference management
- Notification settings
- Theme/UI preferences
- Trading preferences
- Risk tolerance settings

## Deployment Considerations

### Environment Variables
- Email backend configuration
- MFA service credentials
- Security keys and secrets

### Monitoring
- User registration metrics
- Login success/failure rates
- MFA adoption rates
- Role distribution analytics

### Backup Strategy
- User data backup procedures
- Password reset capability
- Account recovery processes

This Users app provides a solid foundation for identity and access management that can scale with the Thor trading platform's growing security and user management needs.

http://localhost:5173/auth/login