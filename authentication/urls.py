from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'auth', views.AuthenticationViewSet, basename='auth')
router.register(r'profile', views.UserProfileViewSet, basename='user-profile')

# URL patterns combining ViewSets and function-based views
urlpatterns = [
    # ViewSet-based endpoints (recommended)
    path('api/v1/', include(router.urls)),
    
    # JWT token refresh
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Legacy endpoints for backward compatibility
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('change-password/', views.change_password, name='change_password'),
]
