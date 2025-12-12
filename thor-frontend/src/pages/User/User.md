# User Module Notes

This document summarizes the current behavior for the `/pages/User` screens (Login, Register, Profile settings) and how they integrate with the updated auth flow.

## Components

- **Login.tsx**
  - Posts to `/api/users/login/` via `api.post('/users/login/', { email, password })`.
  - On success, calls `useAuth().login(accessToken, refreshToken)` so AuthContext writes both tokens and updates the axios Authorization header.
  - Redirect target respects the `?next=` query param (defaults to `/app/home`).

- **Register.tsx**
  - Posts to `/api/users/register/`.
  - After success it redirects to `/auth/login`; registration does not auto-login.

- **User.tsx**
  - Placeholder for profile/account settings UI. Currently shows static fields and will later consume the `/api/users/profile/` endpoint along with ActAndPos APIs.

- **WarRoomBanner**
  - Static marketing/branding banner used on Login page.

## Auth Lifecycle Reminders

- AuthContext (under `src/context/AuthContext.tsx`) is the single owner of JWT state; never read/write tokens directly inside page components.
- Logout is triggered from the drawer’s "Sign out" button (`useAuth().logout()`), which clears both `thor_access_token` and `thor_refresh_token` and removes the axios default Authorization header.
- Protected routes use `useAuth().isAuthenticated` (see `src/components/ProtectedRoute.tsx`). If you add new `/app/user/*` subpages, wrap them with `ProtectedRoute`.

## Future Work

- Wire `User.tsx` to display the authenticated user profile (GET `/api/users/profile/`).
- Add per-user account management once ActAndPos exposes user-scoped endpoints.
- Optionally auto-login users after registration by chaining a login call with the submitted credentials.

Keep this document updated whenever the auth flow or user pages change.
