"""
Finance Module URL Configuration
URL patterns for Finance administration and operations
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Import API views
from .finance_api_views import (
    PendingApplicationsListView,
    ScholarshipCalculationView,
    PaymentStatusUpdateView,
    DBTTransferSimulationView,
    FinanceReportsView,
    FinanceDashboardView,
    BulkDisbursementView,
    FinanceStatisticsView
)

app_name = 'finance'

# Legacy URL patterns (for backward compatibility)
legacy_urlpatterns = [
    path('legacy/schemes/', views.scholarship_schemes, name='scholarship_schemes_legacy'),
    path('legacy/disbursements/', views.disbursements, name='disbursements_legacy'),
    path('legacy/budgets/', views.budgets, name='budgets_legacy'),
    path('legacy/transactions/', views.transactions, name='transactions_legacy'),
    path('legacy/reports/', views.financial_reports, name='financial_reports_legacy'),
    path('legacy/dashboard/', views.finance_dashboard_legacy, name='dashboard_legacy'),
    path('legacy/payment-status/', views.payment_status_legacy, name='payment_status_legacy'),
    path('legacy/calculation/', views.calculation_legacy, name='calculation_legacy'),
    path('api-endpoints/', views.api_endpoints, name='api_endpoints'),
]

# Main API URL patterns for Finance Module
api_urlpatterns = [
    # Application Management
    path('applications/pending/', PendingApplicationsListView.as_view(), name='pending_applications'),
    
    # Scholarship Calculations
    path('calculate/', ScholarshipCalculationView.as_view(), name='scholarship_calculation'),
    
    # Payment Management
    path('payments/status/', PaymentStatusUpdateView.as_view(), name='payment_status_update'),
    path('disbursements/bulk/', BulkDisbursementView.as_view(), name='bulk_disbursements'),
    
    # DBT Operations
    path('dbt/transfer/', DBTTransferSimulationView.as_view(), name='dbt_transfer'),
    
    # Reports and Analytics
    path('dashboard/', FinanceDashboardView.as_view(), name='finance_dashboard'),
    path('statistics/', FinanceStatisticsView.as_view(), name='finance_statistics'),
    path('reports/<str:report_type>/', FinanceReportsView.as_view(), name='finance_reports'),
]

# Combine all URL patterns
urlpatterns = api_urlpatterns + legacy_urlpatterns

# Additional API documentation patterns
documentation_patterns = [
    path('docs/api/', views.api_endpoints, name='api_documentation'),
]

urlpatterns += documentation_patterns
