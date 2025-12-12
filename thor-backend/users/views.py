"""
Views for user authentication and management.
"""
from rest_framework import generics, permissions, status, serializers
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model, authenticate
from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT serializer that accepts username or email for login.
    The CustomUser model uses email as USERNAME_FIELD.
    """
    username_field = User.USERNAME_FIELD  # This is 'email'
    
    def validate(self, attrs):
        # Get the login identifier (could be email or username field value)
        credential = attrs.get(self.username_field)
        password = attrs.get('password')
        
        # Since USERNAME_FIELD is 'email', authenticate expects email
        user = authenticate(username=credential, password=password)
        
        if user is None:
            raise serializers.ValidationError({'non_field_errors': ['Invalid credentials']})
        
        if not user.is_active:
            raise serializers.ValidationError({'non_field_errors': ['User account is disabled']})
        
        # Generate tokens using the authenticated user
        refresh = self.get_token(user)
        
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT login view."""
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    """
    User registration endpoint.
    
    POST /api/users/register/
    {
        "email": "user@example.com",
        "password": "StrongPassw0rd!",
        "password_confirm": "StrongPassw0rd!"
    }
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update user profile.
    Requires authentication.
    
    GET /api/users/profile/
    """
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)
    
    def get_object(self):
        return self.request.user
