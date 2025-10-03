from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router for ViewSets (if you have ViewSets for notifications)
router = DefaultRouter()
# router.register(r'notifications', views.NotificationViewSet, basename='notification')

# Namespace for notifications
app_name = 'notifications'

urlpatterns = [
    # API routes
    path('api/', include(router.urls)),
    
    # Notification management endpoints
    path('api/preferences/', views.NotificationPreferencesView.as_view(), name='notification-preferences'),
    path('api/preferences/update/', views.UpdateNotificationPreferencesView.as_view(), name='update-notification-preferences'),
    
    # Notification testing endpoints (for development/admin)
    path('api/test/email/', views.TestEmailNotificationView.as_view(), name='test-email-notification'),
    path('api/test/application-status/', views.TestApplicationNotificationView.as_view(), name='test-application-notification'),
    
    # Email template management
    path('api/templates/', views.NotificationTemplateListView.as_view(), name='notification-templates'),
    path('api/templates/<int:pk>/', views.NotificationTemplateDetailView.as_view(), name='notification-template-detail'),
    
    # Email logs and statistics
    path('api/logs/', views.EmailLogListView.as_view(), name='email-logs'),
    path('api/stats/', views.NotificationStatsView.as_view(), name='notification-stats'),
    
    # Webhook endpoints for email status updates
    path('api/webhook/email-status/', views.EmailStatusWebhookView.as_view(), name='email-status-webhook'),
]
