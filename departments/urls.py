"""
Department Module URL Configuration
URL patterns for Department administration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Import API views
from .department_api_views import (
    VerifiedApplicationsListView,
    ApplicationReviewView,
    ForwardToFinanceView,
    DepartmentDashboardView,
    DepartmentReportsView,
    DepartmentDetailView,
    DepartmentAdminProfileView,
    ApplicationDetailView,
    BulkApplicationActionView,
    ApplicationWorkflowView,
    DepartmentSettingsView,
    DepartmentStatisticsView,
    CourseListView,
    StudentListView,
    FacultyListView,
    DepartmentChoicesView
)

app_name = 'departments'

# Original views (if needed for backward compatibility)
legacy_urlpatterns = [
    path('legacy/', views.department_list, name='department_list_legacy'),
    path('legacy/<int:department_id>/', views.department_detail, name='department_detail_legacy'),
]

# API URL patterns for Department Administration
api_urlpatterns = [
    # Department Management
    path('profile/', DepartmentDetailView.as_view(), name='department_profile'),
    path('admin/profile/', DepartmentAdminProfileView.as_view(), name='admin_profile'),
    path('settings/', DepartmentSettingsView.as_view(), name='department_settings'),
    path('statistics/', DepartmentStatisticsView.as_view(), name='department_statistics'),
    path('choices/', DepartmentChoicesView.as_view(), name='department_choices'),
    
    # Application Management
    path('applications/verified/', VerifiedApplicationsListView.as_view(), name='verified_applications'),
    path('applications/<str:application_id>/', ApplicationDetailView.as_view(), name='application_detail'),
    path('applications/<str:application_id>/review/', ApplicationReviewView.as_view(), name='application_review'),
    path('applications/<str:application_id>/workflow/', ApplicationWorkflowView.as_view(), name='application_workflow'),
    path('applications/bulk/action/', BulkApplicationActionView.as_view(), name='bulk_application_action'),
    
    # Finance Integration
    path('finance/forward/', ForwardToFinanceView.as_view(), name='forward_to_finance'),
    
    # Dashboard and Reports
    path('dashboard/', DepartmentDashboardView.as_view(), name='department_dashboard'),
    path('reports/<str:report_type>/', DepartmentReportsView.as_view(), name='department_reports'),
    
    # Resource Management
    path('courses/', CourseListView.as_view(), name='course_list'),
    path('students/', StudentListView.as_view(), name='student_list'),
    path('faculty/', FacultyListView.as_view(), name='faculty_list'),
]

# Combine all URL patterns
urlpatterns = api_urlpatterns + legacy_urlpatterns
