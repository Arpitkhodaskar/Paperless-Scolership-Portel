from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'institutes', views.InstituteViewSet, basename='institute')
router.register(r'admins', views.InstituteAdminViewSet, basename='institute-admin')
router.register(r'courses', views.CourseViewSet, basename='course')
router.register(r'specializations', views.CourseSpecializationViewSet, basename='course-specialization')

urlpatterns = [
    # Include ViewSet URLs
    path('api/', include(router.urls)),
    
    # Legacy endpoints (commented out for ViewSet transition)
    # path('', views.institute_list, name='institute_list'),
    # path('<int:institute_id>/', views.institute_detail, name='institute_detail'),
]
