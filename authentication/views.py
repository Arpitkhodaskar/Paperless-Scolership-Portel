from rest_framework import status, viewsets, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import authenticate
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import uuid

from .models import CustomUser, UserProfile
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    UserUpdateSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer
)


class CustomPermissions:
    """Custom permission classes for role-based access"""
    
    class IsStudent(permissions.BasePermission):
        def has_permission(self, request, view):
            return request.user.is_authenticated and request.user.user_type == 'student'
    
    class IsInstituteAdmin(permissions.BasePermission):
        def has_permission(self, request, view):
            return request.user.is_authenticated and request.user.user_type == 'institute_admin'
    
    class IsDepartmentAdmin(permissions.BasePermission):
        def has_permission(self, request, view):
            return request.user.is_authenticated and request.user.user_type == 'department_admin'
    
    class IsFinanceAdmin(permissions.BasePermission):
        def has_permission(self, request, view):
            return request.user.is_authenticated and request.user.user_type == 'finance_admin'
    
    class IsGrievanceAdmin(permissions.BasePermission):
        def has_permission(self, request, view):
            return request.user.is_authenticated and request.user.user_type == 'grievance_admin'
    
    class IsAdminUser(permissions.BasePermission):
        def has_permission(self, request, view):
            return request.user.is_authenticated and request.user.user_type in [
                'institute_admin', 'department_admin', 'finance_admin', 
                'grievance_admin', 'super_admin'
            ]


class AuthenticationViewSet(GenericViewSet):
    """Enhanced authentication viewset with comprehensive auth features"""
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['register', 'login', 'password_reset_request']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """Enhanced user registration endpoint"""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            # Send welcome email (optional)
            if hasattr(settings, 'EMAIL_HOST_USER'):
                try:
                    send_mail(
                        'Welcome to Scholarship Portal',
                        f'Hello {user.get_full_name()}, welcome to the portal!',
                        settings.EMAIL_HOST_USER,
                        [user.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass  # Email sending failed, but registration succeeded
            
            return Response({
                'message': 'User registered successfully',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """Enhanced user login endpoint with session tracking"""
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            remember_me = serializer.validated_data.get('remember_me', False)
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # Generate tokens with custom expiry
            refresh = RefreshToken.for_user(user)
            if remember_me:
                # Extend token lifetime for "remember me"
                refresh.set_exp(lifetime=timezone.timedelta(days=30))
            
            return Response({
                'message': 'Login successful',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """Enhanced logout endpoint with token blacklisting"""
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Invalid token or logout failed'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Get current user profile"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Update current user profile"""
        serializer = UserUpdateSerializer(
            request.user, 
            data=request.data, 
            partial=request.method == 'PATCH',
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully',
                'user': UserSerializer(request.user).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password"""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # Invalidate all existing tokens for security
            refresh = RefreshToken.for_user(user)
            refresh.blacklist()
            
            return Response({
                'message': 'Password changed successfully',
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def password_reset_request(self, request):
        """Request password reset"""
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = CustomUser.objects.get(email=email)
            
            # Generate reset token
            reset_token = str(uuid.uuid4())
            # In production, store this token in cache or database with expiry
            
            # Send reset email
            if hasattr(settings, 'EMAIL_HOST_USER'):
                try:
                    send_mail(
                        'Password Reset Request',
                        f'Use this token to reset your password: {reset_token}',
                        settings.EMAIL_HOST_USER,
                        [email],
                        fail_silently=False,
                    )
                    return Response({
                        'message': 'Password reset email sent successfully'
                    }, status=status.HTTP_200_OK)
                except Exception:
                    return Response({
                        'error': 'Failed to send reset email'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                'message': 'Password reset functionality not configured'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def verify_email(self, request):
        """Email verification endpoint"""
        # Implementation for email verification
        return Response({
            'message': 'Email verification endpoint'
        }, status=status.HTTP_200_OK)


class UserProfileViewSet(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    """ViewSet for user profile management"""
    
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Get current user's profile"""
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
    
    def retrieve(self, request, *args, **kwargs):
        """Get user profile"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """Update user profile"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': 'Profile updated successfully',
            'data': serializer.data
        })


# Legacy API views for backward compatibility
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Legacy registration endpoint"""
    viewset = AuthenticationViewSet()
    viewset.action = 'register'
    return viewset.register(request)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Legacy login endpoint"""
    viewset = AuthenticationViewSet()
    viewset.action = 'login'
    return viewset.login(request)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Legacy logout endpoint"""
    viewset = AuthenticationViewSet()
    viewset.action = 'logout'
    return viewset.logout(request)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """Legacy profile endpoint"""
    viewset = AuthenticationViewSet()
    viewset.action = 'profile'
    return viewset.profile(request)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Legacy update profile endpoint"""
    viewset = AuthenticationViewSet()
    viewset.action = 'update_profile'
    return viewset.update_profile(request)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Legacy change password endpoint"""
    viewset = AuthenticationViewSet()
    viewset.action = 'change_password'
    return viewset.change_password(request)
