# Authentication System - Thor Project

## Overview
Thor now has proper JWT (JSON Web Token) authentication integrated between Django backend and React frontend.

## Backend (Django + JWT)

### Endpoints

**Login** (Get JWT tokens):
```
POST /api/users/login/
Content-Type: application/json

{
  "username": "thor",  // or email: "admin@360edu.org"
  "password": "Coco1464#"
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Refresh Token** (Get new access token):
```
POST /api/users/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Register** (Create new user):
```
POST /api/users/register/
Content-Type: application/json

{
  "username": "newuser",
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "password_confirm": "SecurePassword123!",
  "first_name": "First",
  "last_name": "Last"
}
```

**Get Profile** (Requires authentication):
```
GET /api/users/profile/
Authorization: Bearer <access_token>

Response:
{
  "id": 1,
  "username": "thor",
  "email": "admin@360edu.org",
  "first_name": "Thor",
  "last_name": "Admin",
  "is_staff": true
}
```

### Token Lifetimes
- **Access Token**: 5 hours
- **Refresh Token**: 7 days

### Settings
Location: `thor-backend/thor_project/settings.py`

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

## Frontend (React + TypeScript)

### Login Flow

1. User enters username/password in `/auth/login`
2. Frontend calls `POST /api/users/login/`
3. Store tokens in localStorage:
   - `thor_access_token`
   - `thor_refresh_token`
4. Redirect to user dashboard

### API Interceptor
Location: `thor-frontend/src/services/api.ts`

**Automatic Features:**
- ✅ Adds `Authorization: Bearer <token>` to all requests
- ✅ Auto-refreshes expired access tokens
- ✅ Redirects to login if refresh fails

**Usage in Components:**
```typescript
import api from '../../services/api';

// All API calls automatically include JWT token
const response = await api.get('/api/users/profile/');
```

## Current Users

**Admin/Superuser:**
- Username: `thor`
- Email: `admin@360edu.org`
- Password: `Coco1464#`
- Permissions: Full admin access

## Testing

### Test Login (Browser)
1. Visit: http://localhost:5173/auth/login
2. Enter:
   - Username: `thor`
   - Password: `Coco1464#`
3. Should redirect to `/app/user` with toast "Logged in successfully!"

### Test with curl
```bash
# Get tokens
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "thor", "password": "Coco1464#"}'

# Use access token
curl -X GET http://localhost:8000/api/users/profile/ \
  -H "Authorization: Bearer <your_access_token>"

# Refresh token
curl -X POST http://localhost:8000/api/users/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<your_refresh_token>"}'
```

## Security Notes

### ✅ Implemented
- Password hashing (Django default PBKDF2)
- JWT token-based authentication
- Token refresh mechanism
- CORS configuration
- HTTPS support via Cloudflare Tunnel

### 🔒 Production Checklist
- [ ] Change `SECRET_KEY` in `.env`
- [ ] Set `DEBUG=False` in production
- [ ] Use strong passwords for all users
- [ ] Enable HTTPS only (no HTTP)
- [ ] Add rate limiting to login endpoint
- [ ] Consider adding 2FA for admin users

## Files Modified

**Backend:**
- `requirements.txt` - Added djangorestframework-simplejwt
- `thor_project/settings.py` - JWT configuration
- `thor_project/urls.py` - Added users endpoints
- `users/urls.py` - Created (auth routes)
- `users/views.py` - Login, register, profile views
- `users/serializers.py` - Created (user serialization)

**Frontend:**
- `src/pages/User/Login.tsx` - Connected to real API
- `src/services/api.ts` - JWT interceptor with auto-refresh

## Troubleshooting

**"Invalid credentials" error:**
- Verify username is `thor` (not `admin`)
- Verify password is exactly `Coco1464#`
- Check Django terminal for errors

**Token expired:**
- Frontend should auto-refresh
- If not working, clear localStorage and login again

**CORS errors:**
- Verify Django is running on port 8000
- Verify frontend is on port 5173
- Check `CORS_ALLOWED_ORIGINS` in settings.py

**Can't login to Django admin:**
- Use: http://127.0.0.1:8000/admin/
- Username: `thor`
- Password: `Coco1464#`
