from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router for ViewSets
router = DefaultRouter()
router.register(r'grievances', views.GrievanceViewSet, basename='grievance')
router.register(r'categories', views.GrievanceCategoryViewSet, basename='grievance-category')
router.register(r'comments', views.GrievanceCommentViewSet, basename='grievance-comment')
router.register(r'documents', views.GrievanceDocumentViewSet, basename='grievance-document')
router.register(r'faqs', views.FAQViewSet, basename='faq')
router.register(r'templates', views.GrievanceTemplateViewSet, basename='grievance-template')

# Namespace for grievances
app_name = 'grievances'

urlpatterns = [
    # API routes
    path('api/', include(router.urls)),
    
    # Additional API endpoints that might not fit ViewSet pattern
    path('api/grievances/<uuid:grievance_id>/status-history/', 
         views.GrievanceViewSet.as_view({'get': 'status_history'}), 
         name='grievance-status-history'),
    
    path('api/grievances/<uuid:grievance_id>/escalation-history/', 
         views.GrievanceViewSet.as_view({'get': 'escalation_history'}), 
         name='grievance-escalation-history'),
    
    path('api/grievances/bulk-actions/', 
         views.GrievanceViewSet.as_view({'post': 'bulk_actions'}), 
         name='grievance-bulk-actions'),
    
    path('api/grievances/export/', 
         views.GrievanceViewSet.as_view({'get': 'export_report'}), 
         name='grievance-export'),
    
    path('api/dashboard/stats/', 
         views.GrievanceViewSet.as_view({'get': 'dashboard_stats'}), 
         name='grievance-dashboard-stats'),
    
    path('api/faqs/search/', 
         views.FAQViewSet.as_view({'get': 'search'}), 
         name='faq-search'),
    
    # Template-based routes (existing)
    path('', views.grievance_list, name='grievance_list'),
    path('create/', views.create_grievance, name='create_grievance'),
    path('<str:grievance_id>/', views.grievance_detail, name='grievance_detail'),
    path('<str:grievance_id>/comments/', views.grievance_comments, name='grievance_comments'),
    path('categories/', views.grievance_categories, name='grievance_categories'),
    path('faqs/', views.faqs, name='faqs'),
]
