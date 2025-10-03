"""
Finance Module Views
Legacy function-based views for backward compatibility
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import redirect
from django.urls import reverse

# Import the new API views for delegation
from .finance_api_views import (
    PendingApplicationsListView, ScholarshipCalculationView,
    PaymentStatusUpdateView, DBTTransferSimulationView,
    FinanceReportsView, FinanceDashboardView,
    BulkDisbursementView, FinanceStatisticsView
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scholarship_schemes(request):
    """List scholarship schemes - Legacy endpoint"""
    return Response({
        'message': 'This endpoint has been moved to the new API structure',
        'new_endpoint': '/api/finance/schemes/',
        'status': 'deprecated'
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def disbursements(request):
    """Disbursements management - Legacy endpoint"""
    if request.method == 'GET':
        return Response({
            'message': 'This endpoint has been moved to the new API structure',
            'new_endpoints': {
                'pending_applications': '/api/finance/applications/pending/',
                'disbursements_list': '/api/finance/disbursements/',
                'payment_status_update': '/api/finance/payments/status/',
                'dbt_transfer': '/api/finance/dbt/transfer/'
            },
            'status': 'deprecated'
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        return Response({
            'message': 'POST operations moved to new API endpoints',
            'bulk_disbursement': '/api/finance/disbursements/bulk/',
            'status': 'deprecated'
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def budgets(request):
    """Budgets management - Legacy endpoint"""
    return Response({
        'message': 'This endpoint has been moved to the new API structure',
        'new_endpoints': {
            'budget_list': '/api/finance/budgets/',
            'budget_utilization': '/api/finance/reports/budget_utilization/'
        },
        'status': 'deprecated'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transactions(request):
    """Transactions management - Legacy endpoint"""
    return Response({
        'message': 'This endpoint has been moved to the new API structure',
        'new_endpoints': {
            'transactions_list': '/api/finance/transactions/',
            'transaction_report': '/api/finance/reports/transaction_report/'
        },
        'status': 'deprecated'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_reports(request):
    """Financial reports - Legacy endpoint"""
    return Response({
        'message': 'This endpoint has been moved to the new API structure',
        'new_endpoints': {
            'dashboard': '/api/finance/dashboard/',
            'statistics': '/api/finance/statistics/',
            'reports': '/api/finance/reports/{report_type}/',
            'available_reports': [
                'disbursement_summary',
                'budget_utilization', 
                'transaction_report',
                'institute_financial',
                'scholarship_analytics',
                'payment_status'
            ]
        },
        'status': 'deprecated'
    }, status=status.HTTP_200_OK)


# Additional helper views for backward compatibility
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def finance_dashboard_legacy(request):
    """Legacy dashboard endpoint - redirect to new API"""
    return Response({
        'message': 'Dashboard moved to new API structure',
        'new_endpoint': '/api/finance/dashboard/',
        'redirect_available': True
    }, status=status.HTTP_301_MOVED_PERMANENTLY)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_status_legacy(request):
    """Legacy payment status endpoint"""
    return Response({
        'message': 'Payment status operations moved to new API',
        'new_endpoints': {
            'update_status': '/api/finance/payments/status/',
            'bulk_payments': '/api/finance/disbursements/bulk/',
            'dbt_transfers': '/api/finance/dbt/transfer/'
        },
        'status': 'deprecated'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calculation_legacy(request):
    """Legacy scholarship calculation endpoint"""
    return Response({
        'message': 'Scholarship calculation moved to new API',
        'new_endpoint': '/api/finance/calculate/',
        'method': 'POST',
        'required_fields': ['application_id', 'calculation_type'],
        'status': 'deprecated'
    }, status=status.HTTP_200_OK)


# API endpoint mapping for documentation
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_endpoints(request):
    """List all available finance API endpoints"""
    endpoints = {
        'message': 'Finance Module API Endpoints',
        'version': '1.0',
        'base_url': '/api/finance/',
        'endpoints': {
            'applications': {
                'pending': {
                    'url': '/api/finance/applications/pending/',
                    'method': 'GET',
                    'description': 'List applications pending finance processing',
                    'permissions': 'Finance Admin'
                }
            },
            'calculations': {
                'calculate': {
                    'url': '/api/finance/calculate/',
                    'method': 'POST',
                    'description': 'Calculate scholarship amounts',
                    'permissions': 'Finance Admin'
                }
            },
            'payments': {
                'status_update': {
                    'url': '/api/finance/payments/status/',
                    'method': 'POST',
                    'description': 'Update payment status',
                    'permissions': 'Finance Admin'
                }
            },
            'dbt': {
                'transfer': {
                    'url': '/api/finance/dbt/transfer/',
                    'method': 'POST',
                    'description': 'Simulate DBT transfers',
                    'permissions': 'Finance Admin'
                }
            },
            'disbursements': {
                'bulk': {
                    'url': '/api/finance/disbursements/bulk/',
                    'method': 'POST',
                    'description': 'Bulk disbursement processing',
                    'permissions': 'Finance Admin'
                }
            },
            'reports': {
                'dashboard': {
                    'url': '/api/finance/dashboard/',
                    'method': 'GET',
                    'description': 'Finance dashboard data',
                    'permissions': 'Finance Admin'
                },
                'statistics': {
                    'url': '/api/finance/statistics/',
                    'method': 'GET', 
                    'description': 'Comprehensive finance statistics',
                    'permissions': 'Finance Admin'
                },
                'custom_reports': {
                    'url': '/api/finance/reports/{report_type}/',
                    'method': 'GET',
                    'description': 'Generate custom reports',
                    'permissions': 'Finance Admin',
                    'report_types': [
                        'disbursement_summary',
                        'budget_utilization',
                        'transaction_report', 
                        'institute_financial',
                        'scholarship_analytics',
                        'payment_status'
                    ]
                }
            }
        },
        'authentication': {
            'type': 'JWT',
            'header': 'Authorization: Bearer <token>',
            'required_role': 'Finance Admin'
        }
    }
    
    return Response(endpoints, status=status.HTTP_200_OK)
