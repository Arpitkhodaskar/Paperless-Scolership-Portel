"""
Institute Module API Views
Comprehensive Django REST Framework views for Institute administration
"""

from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg, Sum, F, Case, When, IntegerField, Value
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.core.cache import cache
from django.db import transaction

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

import logging
import csv
import io
from datetime import datetime, timedelta
from collections import defaultdict
import json

from .models import Institute, InstituteAdmin, InstituteBankAccount, InstituteDocument
from students.models import Student, ScholarshipApplication, StudentDocument, DocumentVerification
from .institute_serializers import (
    InstituteSerializer, InstituteAdminSerializer, InstituteDetailSerializer,
    StudentApplicationListSerializer, ApplicationApprovalSerializer,
    ApplicationStatusUpdateSerializer, ApplicationReportSerializer,
    InstituteReportSerializer, ApplicationTrackingSerializer,
    BulkApplicationActionSerializer, ApplicationCommentsSerializer
)
from .permissions import InstituteAdminPermission, InstituteReportsPermission
from authentication.permissions import IsAuthenticated

User = get_user_model()
logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for institute module"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class InstituteApplicationsListView(generics.ListAPIView):
    """
    List student applications pending verification for specific institute
    Supports filtering, searching, and sorting
    """
    serializer_class = StudentApplicationListSerializer
    permission_classes = [InstituteAdminPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['student__student_id', 'student__user__first_name', 'student__user__last_name', 'application_id']
    ordering_fields = ['submitted_at', 'amount_requested', 'priority', 'status']
    ordering = ['-submitted_at']

    def get_queryset(self):
        """Filter applications for institute with comprehensive filtering"""
        user = self.request.user
        institute = user.institute_admin_profile.institute
        
        # Base queryset with optimized queries
        queryset = ScholarshipApplication.objects.select_related(
            'student', 'student__user', 'student__institute', 'student__department',
            'assigned_to', 'reviewed_by', 'approved_by'
        ).prefetch_related(
            'student__documents'
        ).filter(
            student__institute=institute
        )
        
        # Apply status filtering
        status_filter = self.request.query_params.get('status', 'pending_verification')
        if status_filter == 'pending_verification':
            queryset = queryset.filter(
                status__in=['submitted', 'under_review', 'document_verification', 'eligibility_check']
            )
        elif status_filter == 'all':
            pass  # No filter
        else:
            queryset = queryset.filter(status=status_filter)
        
        # Apply additional filters
        scholarship_type = self.request.query_params.get('scholarship_type')
        if scholarship_type:
            queryset = queryset.filter(scholarship_type=scholarship_type)
        
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        academic_year = self.request.query_params.get('academic_year')
        if academic_year:
            queryset = queryset.filter(academic_year=academic_year)
        
        # Date range filtering
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(submitted_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(submitted_at__lte=date_to)
        
        # Amount range filtering
        min_amount = self.request.query_params.get('min_amount')
        max_amount = self.request.query_params.get('max_amount')
        if min_amount:
            queryset = queryset.filter(amount_requested__gte=min_amount)
        if max_amount:
            queryset = queryset.filter(amount_requested__lte=max_amount)
        
        # Department filtering
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(student__department__id=department)
        
        # Course level filtering
        course_level = self.request.query_params.get('course_level')
        if course_level:
            queryset = queryset.filter(student__course_level=course_level)
        
        # Overdue applications
        show_overdue = self.request.query_params.get('show_overdue', 'false').lower() == 'true'
        if show_overdue:
            thirty_days_ago = timezone.now() - timedelta(days=30)
            queryset = queryset.filter(
                submitted_at__lte=thirty_days_ago,
                status__in=['submitted', 'under_review', 'document_verification']
            )
        
        return queryset.distinct()

    @extend_schema(
        summary="List Student Applications for Institute",
        description="Retrieve paginated list of student scholarship applications for the institute with comprehensive filtering options",
        parameters=[
            OpenApiParameter(name='status', description='Filter by application status', required=False, type=str),
            OpenApiParameter(name='scholarship_type', description='Filter by scholarship type', required=False, type=str),
            OpenApiParameter(name='priority', description='Filter by priority level', required=False, type=str),
            OpenApiParameter(name='academic_year', description='Filter by academic year', required=False, type=str),
            OpenApiParameter(name='date_from', description='Filter applications from date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='date_to', description='Filter applications to date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='min_amount', description='Minimum requested amount', required=False, type=float),
            OpenApiParameter(name='max_amount', description='Maximum requested amount', required=False, type=float),
            OpenApiParameter(name='department', description='Filter by department ID', required=False, type=int),
            OpenApiParameter(name='course_level', description='Filter by course level', required=False, type=str),
            OpenApiParameter(name='show_overdue', description='Show only overdue applications', required=False, type=bool),
            OpenApiParameter(name='search', description='Search in student ID, name, or application ID', required=False, type=str),
            OpenApiParameter(name='ordering', description='Order by field (submitted_at, amount_requested, priority, status)', required=False, type=str),
        ],
        responses={200: StudentApplicationListSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        try:
            response = super().get(request, *args, **kwargs)
            
            # Add summary statistics to response
            queryset = self.filter_queryset(self.get_queryset())
            stats = {
                'total_applications': queryset.count(),
                'pending_verification': queryset.filter(status__in=['submitted', 'under_review']).count(),
                'document_verification': queryset.filter(status='document_verification').count(),
                'eligibility_check': queryset.filter(status='eligibility_check').count(),
                'total_amount_requested': float(queryset.aggregate(Sum('amount_requested'))['amount_requested__sum'] or 0),
                'average_amount': float(queryset.aggregate(Avg('amount_requested'))['amount_requested__avg'] or 0),
            }
            
            response.data['summary'] = stats
            return response
            
        except Exception as e:
            logger.error(f"Error in InstituteApplicationsListView: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve applications', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ApplicationApprovalView(APIView):
    """
    Approve or reject scholarship applications with remarks
    Supports both individual and bulk operations
    """
    permission_classes = [InstituteAdminPermission]
    
    @extend_schema(
        summary="Approve/Reject Application",
        description="Approve or reject a scholarship application with detailed remarks and workflow management",
        request=ApplicationApprovalSerializer,
        responses={
            200: ApplicationStatusUpdateSerializer,
            400: {'description': 'Invalid data or application cannot be processed'},
            404: {'description': 'Application not found'},
            403: {'description': 'Permission denied'}
        }
    )
    @transaction.atomic
    def post(self, request, application_id=None):
        """Approve or reject a single application"""
        try:
            # Get institute for permission check
            user = request.user
            institute = user.institute_admin_profile.institute
            
            # Get application
            application = get_object_or_404(
                ScholarshipApplication.objects.select_related('student', 'student__institute'),
                application_id=application_id,
                student__institute=institute
            )
            
            # Validate application can be processed
            if application.status not in ['submitted', 'under_review', 'document_verification', 'eligibility_check']:
                return Response(
                    {'error': f'Application cannot be processed. Current status: {application.status}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = ApplicationApprovalSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            action = serializer.validated_data['action']
            remarks = serializer.validated_data.get('remarks', '')
            internal_notes = serializer.validated_data.get('internal_notes', '')
            approved_amount = serializer.validated_data.get('approved_amount')
            
            # Process the action
            if action == 'approve':
                application.status = 'approved'
                application.approved_by = user
                application.approved_at = timezone.now()
                application.review_comments = remarks
                application.internal_notes = internal_notes
                
                if approved_amount is not None:
                    application.amount_approved = approved_amount
                else:
                    application.amount_approved = application.amount_requested
                    
                logger.info(f"Application {application.application_id} approved by {user.email}")
                
            elif action == 'reject':
                application.status = 'rejected'
                application.rejected_at = timezone.now()
                application.rejection_reason = remarks
                application.internal_notes = internal_notes
                application.reviewed_by = user
                
                logger.info(f"Application {application.application_id} rejected by {user.email}")
                
            elif action == 'request_documents':
                application.status = 'document_verification'
                application.review_comments = remarks
                application.internal_notes = internal_notes
                application.reviewed_by = user
                
                logger.info(f"Documents requested for application {application.application_id}")
                
            elif action == 'hold':
                application.status = 'on_hold'
                application.review_comments = remarks
                application.internal_notes = internal_notes
                application.reviewed_by = user
                
            application.save()
            
            # Create activity log entry
            self._create_activity_log(application, action, remarks, user)
            
            # Return updated application data
            response_serializer = ApplicationStatusUpdateSerializer(application)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except ScholarshipApplication.DoesNotExist:
            return Response(
                {'error': 'Application not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in ApplicationApprovalView: {str(e)}")
            return Response(
                {'error': 'Failed to process application', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Bulk Application Actions",
        description="Perform bulk approve/reject operations on multiple applications",
        request=BulkApplicationActionSerializer,
        responses={
            200: {'description': 'Bulk action completed successfully'},
            400: {'description': 'Invalid data or some applications could not be processed'}
        }
    )
    @transaction.atomic
    def patch(self, request):
        """Bulk approve/reject multiple applications"""
        try:
            user = request.user
            institute = user.institute_admin_profile.institute
            
            serializer = BulkApplicationActionSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            application_ids = serializer.validated_data['application_ids']
            action = serializer.validated_data['action']
            remarks = serializer.validated_data.get('remarks', '')
            
            # Get applications
            applications = ScholarshipApplication.objects.filter(
                application_id__in=application_ids,
                student__institute=institute,
                status__in=['submitted', 'under_review', 'document_verification', 'eligibility_check']
            )
            
            if not applications.exists():
                return Response(
                    {'error': 'No valid applications found for processing'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            processed_count = 0
            failed_applications = []
            
            for application in applications:
                try:
                    if action == 'approve':
                        application.status = 'approved'
                        application.approved_by = user
                        application.approved_at = timezone.now()
                        application.amount_approved = application.amount_requested
                    elif action == 'reject':
                        application.status = 'rejected'
                        application.rejected_at = timezone.now()
                        application.rejection_reason = remarks
                        application.reviewed_by = user
                    
                    application.review_comments = remarks
                    application.save()
                    
                    self._create_activity_log(application, action, remarks, user)
                    processed_count += 1
                    
                except Exception as e:
                    failed_applications.append({
                        'application_id': application.application_id,
                        'error': str(e)
                    })
            
            return Response({
                'message': f'Bulk action completed. {processed_count} applications processed.',
                'processed_count': processed_count,
                'failed_applications': failed_applications
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in bulk application processing: {str(e)}")
            return Response(
                {'error': 'Failed to process bulk action', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _create_activity_log(self, application, action, remarks, user):
        """Create activity log entry for application action"""
        # This can be extended to use a dedicated ActivityLog model
        log_data = {
            'application_id': application.application_id,
            'action': action,
            'remarks': remarks,
            'user': user.email,
            'timestamp': timezone.now().isoformat()
        }
        
        # Store in application's internal notes as JSON
        if application.internal_notes:
            try:
                notes_data = json.loads(application.internal_notes)
                if not isinstance(notes_data, list):
                    notes_data = [notes_data]
            except (json.JSONDecodeError, TypeError):
                notes_data = [{'old_notes': application.internal_notes}]
        else:
            notes_data = []
        
        notes_data.append(log_data)
        application.internal_notes = json.dumps(notes_data, indent=2)


class ApplicationTrackingView(generics.RetrieveAPIView):
    """
    Track scholarship form submissions and application progress
    Provides detailed timeline and status history
    """
    serializer_class = ApplicationTrackingSerializer
    permission_classes = [InstituteAdminPermission]
    lookup_field = 'application_id'
    
    def get_queryset(self):
        """Get applications for the institute"""
        user = self.request.user
        institute = user.institute_admin_profile.institute
        
        return ScholarshipApplication.objects.select_related(
            'student', 'student__user', 'student__institute', 'student__department',
            'assigned_to', 'reviewed_by', 'approved_by'
        ).prefetch_related(
            'student__documents', 'student__documents__verification'
        ).filter(student__institute=institute)
    
    @extend_schema(
        summary="Track Application Progress",
        description="Get detailed tracking information for a scholarship application including timeline, document status, and processing history",
        responses={
            200: ApplicationTrackingSerializer,
            404: {'description': 'Application not found'},
            403: {'description': 'Permission denied'}
        }
    )
    def get(self, request, *args, **kwargs):
        try:
            application = self.get_object()
            
            # Build comprehensive tracking data
            tracking_data = {
                'application': application,
                'timeline': self._build_timeline(application),
                'document_status': self._get_document_status(application),
                'processing_stats': self._get_processing_stats(application),
                'next_steps': self._get_next_steps(application),
                'workflow_history': self._get_workflow_history(application)
            }
            
            serializer = self.get_serializer(tracking_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in ApplicationTrackingView: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve tracking information', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _build_timeline(self, application):
        """Build application timeline"""
        timeline = []
        
        # Application created
        timeline.append({
            'status': 'draft',
            'timestamp': application.created_at,
            'description': 'Application created',
            'user': application.student.user.get_full_name(),
            'details': f'Initial application for {application.scholarship_name}'
        })
        
        # Application submitted
        if application.submitted_at:
            timeline.append({
                'status': 'submitted',
                'timestamp': application.submitted_at,
                'description': 'Application submitted',
                'user': application.student.user.get_full_name(),
                'details': f'Amount requested: ₹{application.amount_requested}'
            })
        
        # Review started
        if application.review_started_at:
            timeline.append({
                'status': 'under_review',
                'timestamp': application.review_started_at,
                'description': 'Review started',
                'user': application.assigned_to.get_full_name() if application.assigned_to else 'System',
                'details': 'Application assigned for review'
            })
        
        # Review completed
        if application.review_completed_at:
            status_desc = 'Approved' if application.status == 'approved' else 'Rejected'
            timeline.append({
                'status': application.status,
                'timestamp': application.review_completed_at,
                'description': f'Application {status_desc.lower()}',
                'user': (application.approved_by or application.reviewed_by).get_full_name() if (application.approved_by or application.reviewed_by) else 'System',
                'details': application.review_comments or application.rejection_reason or ''
            })
        
        return sorted(timeline, key=lambda x: x['timestamp'])
    
    def _get_document_status(self, application):
        """Get document verification status"""
        documents = application.student.documents.all()
        document_status = {
            'total_documents': documents.count(),
            'verified_documents': documents.filter(is_verified=True).count(),
            'pending_documents': documents.filter(is_verified=False).count(),
            'rejected_documents': documents.filter(status='rejected').count(),
            'documents': []
        }
        
        for doc in documents:
            document_status['documents'].append({
                'document_type': doc.document_type,
                'document_name': doc.document_name,
                'status': doc.status,
                'is_verified': doc.is_verified,
                'uploaded_at': doc.uploaded_at,
                'verification_date': doc.verification_date,
                'rejection_reason': doc.rejection_reason
            })
        
        return document_status
    
    def _get_processing_stats(self, application):
        """Get processing statistics"""
        stats = {
            'days_since_submission': None,
            'processing_time': None,
            'is_overdue': application.is_overdue,
            'priority': application.priority,
            'eligibility_score': application.eligibility_score,
            'document_completeness_score': application.document_completeness_score
        }
        
        if application.submitted_at:
            stats['days_since_submission'] = (timezone.now() - application.submitted_at).days
        
        if application.processing_time:
            stats['processing_time'] = application.processing_time
        
        return stats
    
    def _get_next_steps(self, application):
        """Determine next steps based on current status"""
        next_steps = []
        
        if application.status == 'submitted':
            next_steps.append('Assign reviewer for initial assessment')
            next_steps.append('Verify student documents')
        elif application.status == 'under_review':
            next_steps.append('Complete eligibility assessment')
            next_steps.append('Review financial requirements')
        elif application.status == 'document_verification':
            next_steps.append('Student to upload required documents')
            next_steps.append('Verify submitted documents')
        elif application.status == 'eligibility_check':
            next_steps.append('Complete final eligibility verification')
            next_steps.append('Make approval/rejection decision')
        elif application.status == 'approved':
            next_steps.append('Process disbursement')
            next_steps.append('Send approval notification')
        
        return next_steps
    
    def _get_workflow_history(self, application):
        """Get workflow history from internal notes"""
        workflow_history = []
        
        if application.internal_notes:
            try:
                notes_data = json.loads(application.internal_notes)
                if isinstance(notes_data, list):
                    workflow_history = notes_data
            except (json.JSONDecodeError, TypeError):
                pass
        
        return workflow_history


class InstituteReportsView(APIView):
    """
    Generate comprehensive reports for institute administrators
    Includes various report types with export functionality
    """
    permission_classes = [InstituteReportsPermission]
    
    @extend_schema(
        summary="Generate Institute Reports",
        description="Generate various types of reports for institute scholarship management",
        parameters=[
            OpenApiParameter(name='report_type', description='Type of report (summary, detailed, financial, monthly)', required=True, type=str),
            OpenApiParameter(name='date_from', description='Start date for report (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='date_to', description='End date for report (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='format', description='Report format (json, csv, pdf)', required=False, type=str),
            OpenApiParameter(name='department', description='Filter by department ID', required=False, type=int),
            OpenApiParameter(name='scholarship_type', description='Filter by scholarship type', required=False, type=str),
        ],
        responses={
            200: InstituteReportSerializer,
            400: {'description': 'Invalid parameters'},
            403: {'description': 'Permission denied'}
        }
    )
    def get(self, request):
        """Generate and return reports"""
        try:
            user = request.user
            institute = user.institute_admin_profile.institute
            
            # Get report parameters
            report_type = request.query_params.get('report_type', 'summary')
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')
            format_type = request.query_params.get('format', 'json')
            department_id = request.query_params.get('department')
            scholarship_type = request.query_params.get('scholarship_type')
            
            # Validate report type
            valid_report_types = ['summary', 'detailed', 'financial', 'monthly', 'department_wise', 'trend_analysis']
            if report_type not in valid_report_types:
                return Response(
                    {'error': f'Invalid report type. Valid types: {", ".join(valid_report_types)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Build base queryset
            queryset = ScholarshipApplication.objects.filter(student__institute=institute)
            
            # Apply date filtering
            if date_from:
                queryset = queryset.filter(submitted_at__gte=date_from)
            if date_to:
                queryset = queryset.filter(submitted_at__lte=date_to)
            
            # Apply additional filters
            if department_id:
                queryset = queryset.filter(student__department__id=department_id)
            if scholarship_type:
                queryset = queryset.filter(scholarship_type=scholarship_type)
            
            # Generate report based on type
            if report_type == 'summary':
                report_data = self._generate_summary_report(queryset, institute)
            elif report_type == 'detailed':
                report_data = self._generate_detailed_report(queryset, institute)
            elif report_type == 'financial':
                report_data = self._generate_financial_report(queryset, institute)
            elif report_type == 'monthly':
                report_data = self._generate_monthly_report(queryset, institute)
            elif report_type == 'department_wise':
                report_data = self._generate_department_wise_report(queryset, institute)
            elif report_type == 'trend_analysis':
                report_data = self._generate_trend_analysis_report(queryset, institute)
            
            # Return data in requested format
            if format_type == 'csv':
                return self._export_csv(report_data, report_type)
            elif format_type == 'pdf':
                return self._export_pdf(report_data, report_type)
            else:
                serializer = InstituteReportSerializer(report_data)
                return Response(serializer.data, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Error in InstituteReportsView: {str(e)}")
            return Response(
                {'error': 'Failed to generate report', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_summary_report(self, queryset, institute):
        """Generate summary report"""
        total_applications = queryset.count()
        
        # Status breakdown
        status_breakdown = queryset.values('status').annotate(
            count=Count('id'),
            total_amount=Sum('amount_requested'),
            avg_amount=Avg('amount_requested')
        ).order_by('status')
        
        # Scholarship type breakdown
        type_breakdown = queryset.values('scholarship_type').annotate(
            count=Count('id'),
            total_amount=Sum('amount_requested')
        ).order_by('-count')
        
        # Monthly trends (last 12 months)
        monthly_data = queryset.filter(
            submitted_at__gte=timezone.now() - timedelta(days=365)
        ).annotate(
            month=TruncMonth('submitted_at')
        ).values('month').annotate(
            count=Count('id'),
            total_amount=Sum('amount_requested')
        ).order_by('month')
        
        # Key metrics
        approved_applications = queryset.filter(status='approved')
        total_approved_amount = approved_applications.aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0
        total_requested_amount = queryset.aggregate(Sum('amount_requested'))['amount_requested__sum'] or 0
        
        return {
            'report_type': 'summary',
            'institute': institute.name,
            'generated_at': timezone.now(),
            'total_applications': total_applications,
            'total_requested_amount': float(total_requested_amount),
            'total_approved_amount': float(total_approved_amount),
            'approval_rate': (approved_applications.count() / total_applications * 100) if total_applications > 0 else 0,
            'average_processing_time': self._calculate_avg_processing_time(queryset),
            'status_breakdown': list(status_breakdown),
            'type_breakdown': list(type_breakdown),
            'monthly_trends': list(monthly_data)
        }
    
    def _generate_detailed_report(self, queryset, institute):
        """Generate detailed applications report"""
        applications_data = []
        
        for app in queryset.select_related('student', 'student__user', 'student__department'):
            applications_data.append({
                'application_id': app.application_id,
                'student_id': app.student.student_id,
                'student_name': app.student.user.get_full_name(),
                'department': app.student.department.name,
                'course_level': app.student.course_level,
                'scholarship_type': app.scholarship_type,
                'scholarship_name': app.scholarship_name,
                'amount_requested': float(app.amount_requested),
                'amount_approved': float(app.amount_approved or 0),
                'status': app.status,
                'priority': app.priority,
                'submitted_at': app.submitted_at,
                'review_completed_at': app.review_completed_at,
                'processing_time': app.processing_time,
                'eligibility_score': app.eligibility_score,
                'document_completeness_score': app.document_completeness_score
            })
        
        return {
            'report_type': 'detailed',
            'institute': institute.name,
            'generated_at': timezone.now(),
            'total_records': len(applications_data),
            'applications': applications_data
        }
    
    def _generate_financial_report(self, queryset, institute):
        """Generate financial analysis report"""
        # Amount distribution by status
        financial_summary = queryset.aggregate(
            total_requested=Sum('amount_requested'),
            total_approved=Sum('amount_approved'),
            avg_requested=Avg('amount_requested'),
            avg_approved=Avg('amount_approved')
        )
        
        # Amount ranges analysis
        amount_ranges = [
            {'range': '0-25000', 'min': 0, 'max': 25000},
            {'range': '25001-50000', 'min': 25001, 'max': 50000},
            {'range': '50001-100000', 'min': 50001, 'max': 100000},
            {'range': '100000+', 'min': 100001, 'max': float('inf')}
        ]
        
        range_analysis = []
        for range_data in amount_ranges:
            if range_data['max'] == float('inf'):
                count = queryset.filter(amount_requested__gte=range_data['min']).count()
                total = queryset.filter(amount_requested__gte=range_data['min']).aggregate(Sum('amount_requested'))['amount_requested__sum'] or 0
            else:
                count = queryset.filter(
                    amount_requested__gte=range_data['min'],
                    amount_requested__lte=range_data['max']
                ).count()
                total = queryset.filter(
                    amount_requested__gte=range_data['min'],
                    amount_requested__lte=range_data['max']
                ).aggregate(Sum('amount_requested'))['amount_requested__sum'] or 0
            
            range_analysis.append({
                'range': range_data['range'],
                'count': count,
                'total_amount': float(total),
                'percentage': (count / queryset.count() * 100) if queryset.count() > 0 else 0
            })
        
        return {
            'report_type': 'financial',
            'institute': institute.name,
            'generated_at': timezone.now(),
            'financial_summary': financial_summary,
            'amount_range_analysis': range_analysis,
            'top_scholarship_types': list(
                queryset.values('scholarship_type').annotate(
                    total_amount=Sum('amount_requested')
                ).order_by('-total_amount')[:5]
            )
        }
    
    def _generate_monthly_report(self, queryset, institute):
        """Generate monthly trends report"""
        monthly_data = []
        
        # Get data for last 12 months
        for i in range(12):
            month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            month_queryset = queryset.filter(
                submitted_at__gte=month_start,
                submitted_at__lte=month_end
            )
            
            monthly_data.append({
                'month': month_start.strftime('%Y-%m'),
                'total_applications': month_queryset.count(),
                'approved_applications': month_queryset.filter(status='approved').count(),
                'rejected_applications': month_queryset.filter(status='rejected').count(),
                'total_amount_requested': float(month_queryset.aggregate(Sum('amount_requested'))['amount_requested__sum'] or 0),
                'total_amount_approved': float(month_queryset.aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0)
            })
        
        return {
            'report_type': 'monthly',
            'institute': institute.name,
            'generated_at': timezone.now(),
            'monthly_data': list(reversed(monthly_data))
        }
    
    def _generate_department_wise_report(self, queryset, institute):
        """Generate department-wise analysis report"""
        dept_data = queryset.values(
            'student__department__name',
            'student__department__id'
        ).annotate(
            total_applications=Count('id'),
            approved_applications=Count('id', filter=Q(status='approved')),
            total_amount_requested=Sum('amount_requested'),
            total_amount_approved=Sum('amount_approved'),
            avg_processing_time=Avg(
                Case(
                    When(review_completed_at__isnull=False, then=F('review_completed_at') - F('submitted_at')),
                    default=None,
                    output_field=IntegerField()
                )
            )
        ).order_by('-total_applications')
        
        return {
            'report_type': 'department_wise',
            'institute': institute.name,
            'generated_at': timezone.now(),
            'department_analysis': list(dept_data)
        }
    
    def _generate_trend_analysis_report(self, queryset, institute):
        """Generate trend analysis report"""
        # Weekly trends for last 8 weeks
        weekly_trends = []
        for i in range(8):
            week_start = timezone.now() - timedelta(weeks=i+1)
            week_end = timezone.now() - timedelta(weeks=i)
            
            week_data = queryset.filter(
                submitted_at__gte=week_start,
                submitted_at__lt=week_end
            ).aggregate(
                count=Count('id'),
                amount=Sum('amount_requested')
            )
            
            weekly_trends.append({
                'week': f"Week {i+1}",
                'start_date': week_start.date(),
                'applications': week_data['count'] or 0,
                'total_amount': float(week_data['amount'] or 0)
            })
        
        return {
            'report_type': 'trend_analysis',
            'institute': institute.name,
            'generated_at': timezone.now(),
            'weekly_trends': list(reversed(weekly_trends)),
            'growth_metrics': self._calculate_growth_metrics(queryset)
        }
    
    def _calculate_avg_processing_time(self, queryset):
        """Calculate average processing time"""
        completed_apps = queryset.filter(
            review_completed_at__isnull=False,
            submitted_at__isnull=False
        )
        
        if completed_apps.exists():
            avg_seconds = completed_apps.aggregate(
                avg_time=Avg(F('review_completed_at') - F('submitted_at'))
            )['avg_time']
            
            if avg_seconds:
                return avg_seconds.total_seconds() / 86400  # Convert to days
        
        return 0
    
    def _calculate_growth_metrics(self, queryset):
        """Calculate growth metrics"""
        current_month = timezone.now().replace(day=1)
        previous_month = (current_month - timedelta(days=1)).replace(day=1)
        
        current_count = queryset.filter(submitted_at__gte=current_month).count()
        previous_count = queryset.filter(
            submitted_at__gte=previous_month,
            submitted_at__lt=current_month
        ).count()
        
        growth_rate = 0
        if previous_count > 0:
            growth_rate = ((current_count - previous_count) / previous_count) * 100
        
        return {
            'current_month_applications': current_count,
            'previous_month_applications': previous_count,
            'growth_rate': round(growth_rate, 2)
        }
    
    def _export_csv(self, report_data, report_type):
        """Export report as CSV"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers and data based on report type
        if report_type == 'detailed' and 'applications' in report_data:
            # Headers
            headers = [
                'Application ID', 'Student ID', 'Student Name', 'Department',
                'Course Level', 'Scholarship Type', 'Amount Requested',
                'Amount Approved', 'Status', 'Submitted At'
            ]
            writer.writerow(headers)
            
            # Data
            for app in report_data['applications']:
                writer.writerow([
                    app['application_id'], app['student_id'], app['student_name'],
                    app['department'], app['course_level'], app['scholarship_type'],
                    app['amount_requested'], app['amount_approved'], app['status'],
                    app['submitted_at']
                ])
        
        # Create HTTP response
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{timezone.now().strftime("%Y%m%d")}.csv"'
        return response
    
    def _export_pdf(self, report_data, report_type):
        """Export report as PDF (placeholder)"""
        # This would typically use libraries like reportlab or weasyprint
        # For now, return a simple text response
        response = HttpResponse(
            f"PDF export for {report_type} report would be generated here",
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response


class ApplicationCommentsView(APIView):
    """
    Add and retrieve comments for applications
    Supports threaded discussions and notifications
    """
    permission_classes = [InstituteAdminPermission]
    
    @extend_schema(
        summary="Add Comment to Application",
        description="Add a comment or note to a scholarship application",
        request=ApplicationCommentsSerializer,
        responses={
            201: {'description': 'Comment added successfully'},
            400: {'description': 'Invalid data'},
            404: {'description': 'Application not found'}
        }
    )
    def post(self, request, application_id):
        """Add comment to application"""
        try:
            user = request.user
            institute = user.institute_admin_profile.institute
            
            application = get_object_or_404(
                ScholarshipApplication,
                application_id=application_id,
                student__institute=institute
            )
            
            serializer = ApplicationCommentsSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            comment_text = serializer.validated_data['comment']
            is_internal = serializer.validated_data.get('is_internal', False)
            
            # Create comment entry
            comment_data = {
                'user': user.get_full_name(),
                'user_email': user.email,
                'comment': comment_text,
                'is_internal': is_internal,
                'timestamp': timezone.now().isoformat()
            }
            
            # Add to application's internal notes
            if application.internal_notes:
                try:
                    notes_data = json.loads(application.internal_notes)
                    if not isinstance(notes_data, list):
                        notes_data = [notes_data]
                except (json.JSONDecodeError, TypeError):
                    notes_data = []
            else:
                notes_data = []
            
            notes_data.append(comment_data)
            application.internal_notes = json.dumps(notes_data, indent=2)
            application.save()
            
            return Response(
                {'message': 'Comment added successfully', 'comment_id': len(notes_data)},
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error adding comment: {str(e)}")
            return Response(
                {'error': 'Failed to add comment', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get(self, request, application_id):
        """Get comments for application"""
        try:
            user = request.user
            institute = user.institute_admin_profile.institute
            
            application = get_object_or_404(
                ScholarshipApplication,
                application_id=application_id,
                student__institute=institute
            )
            
            comments = []
            if application.internal_notes:
                try:
                    notes_data = json.loads(application.internal_notes)
                    if isinstance(notes_data, list):
                        comments = [note for note in notes_data if 'comment' in note]
                except (json.JSONDecodeError, TypeError):
                    pass
            
            return Response({'comments': comments}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error retrieving comments: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve comments', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Dashboard and Statistics Views
class InstituteDashboardView(APIView):
    """
    Institute dashboard with key metrics and charts
    """
    permission_classes = [InstituteAdminPermission]
    
    @extend_schema(
        summary="Institute Dashboard Data",
        description="Get dashboard data with key metrics, charts, and recent activities",
        responses={200: {'description': 'Dashboard data retrieved successfully'}}
    )
    def get(self, request):
        try:
            user = request.user
            institute = user.institute_admin_profile.institute
            
            # Get cached dashboard data
            cache_key = f"institute_dashboard_{institute.id}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                return Response(cached_data, status=status.HTTP_200_OK)
            
            # Generate dashboard data
            dashboard_data = self._generate_dashboard_data(institute)
            
            # Cache for 30 minutes
            cache.set(cache_key, dashboard_data, 1800)
            
            return Response(dashboard_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in InstituteDashboardView: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve dashboard data', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_dashboard_data(self, institute):
        """Generate comprehensive dashboard data"""
        applications = ScholarshipApplication.objects.filter(student__institute=institute)
        
        # Key metrics
        total_applications = applications.count()
        pending_applications = applications.filter(
            status__in=['submitted', 'under_review', 'document_verification']
        ).count()
        approved_applications = applications.filter(status='approved').count()
        rejected_applications = applications.filter(status='rejected').count()
        
        # Financial metrics
        total_requested = applications.aggregate(Sum('amount_requested'))['amount_requested__sum'] or 0
        total_approved = applications.aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0
        
        # Recent applications (last 7 days)
        recent_applications = applications.filter(
            submitted_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Status distribution
        status_distribution = list(applications.values('status').annotate(
            count=Count('id')
        ).order_by('-count'))
        
        # Monthly trends (last 6 months)
        monthly_trends = []
        for i in range(6):
            month_start = (timezone.now().replace(day=1) - timedelta(days=30*i))
            month_end = month_start + timedelta(days=32)
            month_end = month_end.replace(day=1) - timedelta(days=1)
            
            month_count = applications.filter(
                submitted_at__gte=month_start,
                submitted_at__lte=month_end
            ).count()
            
            monthly_trends.append({
                'month': month_start.strftime('%Y-%m'),
                'count': month_count
            })
        
        # Top scholarship types
        top_scholarship_types = list(applications.values('scholarship_type').annotate(
            count=Count('id'),
            total_amount=Sum('amount_requested')
        ).order_by('-count')[:5])
        
        # Overdue applications
        overdue_applications = applications.filter(
            submitted_at__lte=timezone.now() - timedelta(days=30),
            status__in=['submitted', 'under_review', 'document_verification']
        ).count()
        
        return {
            'institute_name': institute.name,
            'generated_at': timezone.now(),
            'key_metrics': {
                'total_applications': total_applications,
                'pending_applications': pending_applications,
                'approved_applications': approved_applications,
                'rejected_applications': rejected_applications,
                'approval_rate': (approved_applications / total_applications * 100) if total_applications > 0 else 0,
                'total_amount_requested': float(total_requested),
                'total_amount_approved': float(total_approved),
                'recent_applications': recent_applications,
                'overdue_applications': overdue_applications
            },
            'charts': {
                'status_distribution': status_distribution,
                'monthly_trends': list(reversed(monthly_trends)),
                'scholarship_types': top_scholarship_types
            },
            'alerts': {
                'overdue_count': overdue_applications,
                'pending_documents': 0,  # Calculate separately if needed
                'high_priority_pending': applications.filter(
                    priority='high',
                    status__in=['submitted', 'under_review']
                ).count()
            }
        }


# URL Configuration for Institute API views will be created separately
"""
URL patterns for institute API views:

urlpatterns = [
    path('applications/', InstituteApplicationsListView.as_view(), name='institute-applications'),
    path('applications/<str:application_id>/approve/', ApplicationApprovalView.as_view(), name='application-approval'),
    path('applications/bulk-action/', ApplicationApprovalView.as_view(), name='bulk-application-action'),
    path('applications/<str:application_id>/track/', ApplicationTrackingView.as_view(), name='application-tracking'),
    path('applications/<str:application_id>/comments/', ApplicationCommentsView.as_view(), name='application-comments'),
    path('reports/', InstituteReportsView.as_view(), name='institute-reports'),
    path('dashboard/', InstituteDashboardView.as_view(), name='institute-dashboard'),
]
"""
