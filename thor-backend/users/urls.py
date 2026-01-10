"""
URL configuration for user authentication.
"""
from django.urls import path
from .views import (
    RegisterView,
    UserProfileView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
)

app_name = 'users'

urlpatterns = [
    # JWT Token endpoints
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    
    # User management
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='profile'),
]
