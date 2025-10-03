"""
Institute Module URL Configuration
URL patterns for Institute administration APIs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .institute_api_views import (
    InstituteApplicationsListView,
    ApplicationApprovalView,
    ApplicationTrackingView,
    InstituteReportsView,
    ApplicationCommentsView,
    InstituteDashboardView,
)
from .views import (
    InstituteViewSet,
    InstituteAdminViewSet,
    InstituteDocumentViewSet,
    InstituteBankAccountViewSet,
    StudentVerificationViewSet,
    DocumentVerificationViewSet,
)

app_name = 'institutes'

# Create router for ViewSets
router = DefaultRouter()
router.register(r'institutes', InstituteViewSet, basename='institute')
router.register(r'admins', InstituteAdminViewSet, basename='institute-admin')
router.register(r'documents', InstituteDocumentViewSet, basename='institute-document')
router.register(r'bank-accounts', InstituteBankAccountViewSet, basename='bank-account')
router.register(r'student-verification', StudentVerificationViewSet, basename='student-verification')
router.register(r'document-verification', DocumentVerificationViewSet, basename='document-verification')

urlpatterns = [
    # Include router URLs
    path('api/', include(router.urls)),
    
    # Institute Application Management URLs
    path('api/applications/', InstituteApplicationsListView.as_view(), name='institute-applications-list'),
    path('api/applications/<str:application_id>/approve/', ApplicationApprovalView.as_view(), name='application-approval'),
    path('api/applications/bulk-action/', ApplicationApprovalView.as_view(), name='bulk-application-action'),
    path('api/applications/<str:application_id>/track/', ApplicationTrackingView.as_view(), name='application-tracking'),
    path('api/applications/<str:application_id>/comments/', ApplicationCommentsView.as_view(), name='application-comments'),
    
    # Institute Reports URLs
    path('api/reports/', InstituteReportsView.as_view(), name='institute-reports'),
    path('api/reports/export/', InstituteReportsView.as_view(), name='institute-reports-export'),
    
    # Institute Dashboard URL
    path('api/dashboard/', InstituteDashboardView.as_view(), name='institute-dashboard'),
    
    # Additional Institute Management URLs
    path('api/applications/pending/', InstituteApplicationsListView.as_view(), {'status': 'pending_verification'}, name='pending-applications'),
    path('api/applications/approved/', InstituteApplicationsListView.as_view(), {'status': 'approved'}, name='approved-applications'),
    path('api/applications/rejected/', InstituteApplicationsListView.as_view(), {'status': 'rejected'}, name='rejected-applications'),
    path('api/applications/overdue/', InstituteApplicationsListView.as_view(), {'show_overdue': 'true'}, name='overdue-applications'),
    
    # Student Management URLs
    path('api/students/', include([
        path('', StudentVerificationViewSet.as_view({'get': 'list', 'post': 'create'}), name='students-list'),
        path('<int:pk>/', StudentVerificationViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='student-detail'),
        path('<int:pk>/verify/', StudentVerificationViewSet.as_view({'post': 'verify_student'}), name='student-verify'),
        path('<int:pk>/documents/', DocumentVerificationViewSet.as_view({'get': 'list'}), name='student-documents'),
    ])),
    
    # Document Management URLs
    path('api/documents/', include([
        path('verify/<int:document_id>/', DocumentVerificationViewSet.as_view({'post': 'verify_document'}), name='document-verify'),
        path('bulk-verify/', DocumentVerificationViewSet.as_view({'post': 'bulk_verify_documents'}), name='documents-bulk-verify'),
        path('pending/', DocumentVerificationViewSet.as_view({'get': 'pending_documents'}), name='pending-documents'),
        path('rejected/', DocumentVerificationViewSet.as_view({'get': 'rejected_documents'}), name='rejected-documents'),
    ])),
    
    # Analytics and Statistics URLs
    path('api/analytics/', include([
        path('summary/', InstituteDashboardView.as_view(), name='analytics-summary'),
        path('trends/', InstituteReportsView.as_view(), {'report_type': 'trend_analysis'}, name='analytics-trends'),
        path('departments/', InstituteReportsView.as_view(), {'report_type': 'department_wise'}, name='analytics-departments'),
        path('financial/', InstituteReportsView.as_view(), {'report_type': 'financial'}, name='analytics-financial'),
    ])),
]

# Additional patterns for specific views
application_patterns = [
    path('applications/', include([
        path('', InstituteApplicationsListView.as_view(), name='applications-list'),
        path('pending/', InstituteApplicationsListView.as_view(), {'filter_status': 'pending'}, name='applications-pending'),
        path('under-review/', InstituteApplicationsListView.as_view(), {'filter_status': 'under_review'}, name='applications-under-review'),
        path('approved/', InstituteApplicationsListView.as_view(), {'filter_status': 'approved'}, name='applications-approved'),
        path('rejected/', InstituteApplicationsListView.as_view(), {'filter_status': 'rejected'}, name='applications-rejected'),
        path('high-priority/', InstituteApplicationsListView.as_view(), {'filter_priority': 'high'}, name='applications-high-priority'),
        path('overdue/', InstituteApplicationsListView.as_view(), {'show_overdue': True}, name='applications-overdue'),
        
        path('<str:application_id>/', include([
            path('', ApplicationTrackingView.as_view(), name='application-detail'),
            path('approve/', ApplicationApprovalView.as_view(), name='application-approve'),
            path('reject/', ApplicationApprovalView.as_view(), name='application-reject'),
            path('track/', ApplicationTrackingView.as_view(), name='application-track'),
            path('comments/', ApplicationCommentsView.as_view(), name='application-comments'),
            path('documents/', DocumentVerificationViewSet.as_view({'get': 'application_documents'}), name='application-documents'),
            path('timeline/', ApplicationTrackingView.as_view(), name='application-timeline'),
        ])),
        
        path('bulk/', include([
            path('approve/', ApplicationApprovalView.as_view(), name='bulk-approve'),
            path('reject/', ApplicationApprovalView.as_view(), name='bulk-reject'),
            path('assign/', ApplicationApprovalView.as_view(), name='bulk-assign'),
        ])),
    ])),
]

# Reports patterns
reports_patterns = [
    path('reports/', include([
        path('', InstituteReportsView.as_view(), name='reports-list'),
        path('summary/', InstituteReportsView.as_view(), {'report_type': 'summary'}, name='reports-summary'),
        path('detailed/', InstituteReportsView.as_view(), {'report_type': 'detailed'}, name='reports-detailed'),
        path('financial/', InstituteReportsView.as_view(), {'report_type': 'financial'}, name='reports-financial'),
        path('monthly/', InstituteReportsView.as_view(), {'report_type': 'monthly'}, name='reports-monthly'),
        path('department-wise/', InstituteReportsView.as_view(), {'report_type': 'department_wise'}, name='reports-department-wise'),
        path('trend-analysis/', InstituteReportsView.as_view(), {'report_type': 'trend_analysis'}, name='reports-trend-analysis'),
        
        path('export/', include([
            path('csv/', InstituteReportsView.as_view(), {'format': 'csv'}, name='reports-export-csv'),
            path('pdf/', InstituteReportsView.as_view(), {'format': 'pdf'}, name='reports-export-pdf'),
            path('excel/', InstituteReportsView.as_view(), {'format': 'excel'}, name='reports-export-excel'),
        ])),
    ])),
]

# Management patterns
management_patterns = [
    path('management/', include([
        path('dashboard/', InstituteDashboardView.as_view(), name='management-dashboard'),
        path('settings/', InstituteViewSet.as_view({'get': 'retrieve', 'put': 'update'}), name='management-settings'),
        path('admins/', InstituteAdminViewSet.as_view({'get': 'list', 'post': 'create'}), name='management-admins'),
        path('bank-accounts/', InstituteBankAccountViewSet.as_view({'get': 'list', 'post': 'create'}), name='management-bank-accounts'),
        path('documents/', InstituteDocumentViewSet.as_view({'get': 'list', 'post': 'create'}), name='management-documents'),
    ])),
]

# Combine all patterns
urlpatterns.extend(application_patterns)
urlpatterns.extend(reports_patterns)
urlpatterns.extend(management_patterns)

# API versioning patterns (if needed in future)
v1_patterns = [
    path('v1/', include([
        path('', include(urlpatterns)),
    ])),
]

# Add API versioning if needed
# urlpatterns = v1_patterns
