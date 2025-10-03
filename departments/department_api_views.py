"""
Department Admin Module API Views
Comprehensive Django REST Framework views for Department administration
"""

from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, Avg, F, Case, When, IntegerField, Value
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.core.cache import cache
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings

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
import requests

from .models import Department, DepartmentAdmin, Course, Subject, Faculty
from students.models import Student, ScholarshipApplication, StudentDocument, DocumentVerification
from .department_serializers import (
    DepartmentSerializer, DepartmentAdminSerializer, DepartmentDetailSerializer,
    VerifiedApplicationListSerializer, ApplicationReviewSerializer,
    ApplicationForwardSerializer, DepartmentDashboardSerializer,
    DepartmentReportSerializer, ApplicationDecisionSerializer,
    ForwardedApplicationTrackingSerializer, DepartmentStatisticsSerializer
)
from .permissions import DepartmentAdminPermission, DepartmentReportsPermission
from authentication.permissions import IsAuthenticated

User = get_user_model()
logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for department module"""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class VerifiedApplicationsListView(generics.ListAPIView):
    """
    List verified scholarship applications for department review
    Only shows applications that have been verified by institutes
    """
    serializer_class = VerifiedApplicationListSerializer
    permission_classes = [DepartmentAdminPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['student__student_id', 'student__user__first_name', 'student__user__last_name', 'application_id']
    ordering_fields = ['submitted_at', 'amount_requested', 'priority', 'review_started_at']
    ordering = ['-submitted_at']

    def get_queryset(self):
        """Filter applications for department with comprehensive filtering"""
        user = self.request.user
        department = user.department_admin_profile.department
        
        # Base queryset - only verified applications from institute
        queryset = ScholarshipApplication.objects.select_related(
            'student', 'student__user', 'student__institute', 'student__department',
            'assigned_to', 'reviewed_by', 'approved_by'
        ).prefetch_related(
            'student__documents'
        ).filter(
            student__department=department,
            status__in=['approved', 'partially_approved'],  # Only institute-approved applications
            student__is_verified=True  # Only verified students
        )
        
        # Apply status filtering for department review
        dept_status = self.request.query_params.get('dept_status', 'pending_review')
        if dept_status == 'pending_review':
            # Applications awaiting department review
            queryset = queryset.filter(
                Q(status='approved') | Q(status='partially_approved')
            ).exclude(
                # Exclude already processed by department
                internal_notes__icontains='DEPT_APPROVED'
            ).exclude(
                internal_notes__icontains='DEPT_REJECTED'
            )
        elif dept_status == 'dept_approved':
            queryset = queryset.filter(internal_notes__icontains='DEPT_APPROVED')
        elif dept_status == 'dept_rejected':
            queryset = queryset.filter(internal_notes__icontains='DEPT_REJECTED')
        elif dept_status == 'forwarded_to_finance':
            queryset = queryset.filter(internal_notes__icontains='FORWARDED_TO_FINANCE')
        
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
        
        # Amount range filtering
        min_amount = self.request.query_params.get('min_amount')
        max_amount = self.request.query_params.get('max_amount')
        if min_amount:
            queryset = queryset.filter(amount_approved__gte=min_amount)
        if max_amount:
            queryset = queryset.filter(amount_approved__lte=max_amount)
        
        # Course filtering
        course = self.request.query_params.get('course')
        if course:
            queryset = queryset.filter(student__course_name__icontains=course)
        
        # Date range filtering for department review
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(approved_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(approved_at__lte=date_to)
        
        return queryset.distinct()

    @extend_schema(
        summary="List Verified Applications for Department Review",
        description="Retrieve paginated list of institute-verified scholarship applications for department review",
        parameters=[
            OpenApiParameter(name='dept_status', description='Department review status', required=False, type=str),
            OpenApiParameter(name='scholarship_type', description='Filter by scholarship type', required=False, type=str),
            OpenApiParameter(name='priority', description='Filter by priority level', required=False, type=str),
            OpenApiParameter(name='academic_year', description='Filter by academic year', required=False, type=str),
            OpenApiParameter(name='min_amount', description='Minimum approved amount', required=False, type=float),
            OpenApiParameter(name='max_amount', description='Maximum approved amount', required=False, type=float),
            OpenApiParameter(name='course', description='Filter by course name', required=False, type=str),
            OpenApiParameter(name='date_from', description='Filter from date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='date_to', description='Filter to date (YYYY-MM-DD)', required=False, type=str),
        ],
        responses={200: VerifiedApplicationListSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        try:
            response = super().get(request, *args, **kwargs)
            
            # Add summary statistics
            queryset = self.filter_queryset(self.get_queryset())
            stats = {
                'total_verified_applications': queryset.count(),
                'pending_dept_review': queryset.exclude(
                    Q(internal_notes__icontains='DEPT_APPROVED') | 
                    Q(internal_notes__icontains='DEPT_REJECTED')
                ).count(),
                'dept_approved': queryset.filter(internal_notes__icontains='DEPT_APPROVED').count(),
                'dept_rejected': queryset.filter(internal_notes__icontains='DEPT_REJECTED').count(),
                'forwarded_to_finance': queryset.filter(internal_notes__icontains='FORWARDED_TO_FINANCE').count(),
                'total_amount_approved': float(queryset.aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0),
                'average_amount': float(queryset.aggregate(Avg('amount_approved'))['amount_approved__avg'] or 0),
            }
            
            response.data['summary'] = stats
            return response
            
        except Exception as e:
            logger.error(f"Error in VerifiedApplicationsListView: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve applications', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ApplicationReviewView(APIView):
    """
    Review verified applications - approve/reject at department level
    """
    permission_classes = [DepartmentAdminPermission]
    
    @extend_schema(
        summary="Review Application at Department Level",
        description="Approve or reject an institute-verified application at department level",
        request=ApplicationReviewSerializer,
        responses={
            200: ApplicationDecisionSerializer,
            400: {'description': 'Invalid data or application cannot be processed'},
            404: {'description': 'Application not found'},
            403: {'description': 'Permission denied'}
        }
    )
    @transaction.atomic
    def post(self, request, application_id=None):
        """Review and approve/reject application at department level"""
        try:
            # Get department for permission check
            user = request.user
            department = user.department_admin_profile.department
            
            # Get application
            application = get_object_or_404(
                ScholarshipApplication.objects.select_related('student', 'student__department'),
                application_id=application_id,
                student__department=department
            )
            
            # Validate application can be processed by department
            if application.status not in ['approved', 'partially_approved']:
                return Response(
                    {'error': f'Application must be institute-approved first. Current status: {application.status}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if already processed by department
            if (application.internal_notes and 
                ('DEPT_APPROVED' in application.internal_notes or 'DEPT_REJECTED' in application.internal_notes)):
                return Response(
                    {'error': 'Application has already been processed by department'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = ApplicationReviewSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            action = serializer.validated_data['action']
            dept_remarks = serializer.validated_data.get('dept_remarks', '')
            internal_notes = serializer.validated_data.get('internal_notes', '')
            final_approved_amount = serializer.validated_data.get('final_approved_amount')
            
            # Process the department decision
            if action == 'dept_approve':
                # Department approves the application
                if final_approved_amount is not None:
                    application.amount_approved = final_approved_amount
                
                # Add department approval to internal notes
                dept_decision = {
                    'action': 'DEPT_APPROVED',
                    'dept_remarks': dept_remarks,
                    'internal_notes': internal_notes,
                    'final_approved_amount': float(application.amount_approved),
                    'approved_by': user.email,
                    'department': department.name,
                    'timestamp': timezone.now().isoformat()
                }
                
                # Update internal notes
                if application.internal_notes:
                    try:
                        notes_data = json.loads(application.internal_notes)
                        if not isinstance(notes_data, list):
                            notes_data = [notes_data]
                    except (json.JSONDecodeError, TypeError):
                        notes_data = [{'old_notes': application.internal_notes}]
                else:
                    notes_data = []
                
                notes_data.append(dept_decision)
                application.internal_notes = json.dumps(notes_data, indent=2)
                
                # Update review comments
                if application.review_comments:
                    application.review_comments += f"\n\nDepartment Review: {dept_remarks}"
                else:
                    application.review_comments = f"Department Review: {dept_remarks}"
                
                application.save()
                
                logger.info(f"Application {application.application_id} approved by department {department.name}")
                
                message = 'Application approved by department. Ready for forwarding to finance.'
                
            elif action == 'dept_reject':
                # Department rejects the application
                dept_decision = {
                    'action': 'DEPT_REJECTED',
                    'dept_remarks': dept_remarks,
                    'internal_notes': internal_notes,
                    'rejected_by': user.email,
                    'department': department.name,
                    'timestamp': timezone.now().isoformat()
                }
                
                # Update internal notes
                if application.internal_notes:
                    try:
                        notes_data = json.loads(application.internal_notes)
                        if not isinstance(notes_data, list):
                            notes_data = [notes_data]
                    except (json.JSONDecodeError, TypeError):
                        notes_data = [{'old_notes': application.internal_notes}]
                else:
                    notes_data = []
                
                notes_data.append(dept_decision)
                application.internal_notes = json.dumps(notes_data, indent=2)
                
                # Update status to rejected
                application.status = 'rejected'
                application.rejection_reason = f"Department Rejection: {dept_remarks}"
                application.rejected_at = timezone.now()
                
                application.save()
                
                logger.info(f"Application {application.application_id} rejected by department {department.name}")
                
                message = 'Application rejected by department.'
            
            # Return updated application data
            response_serializer = ApplicationDecisionSerializer(application)
            response_data = response_serializer.data
            response_data['message'] = message
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ScholarshipApplication.DoesNotExist:
            return Response(
                {'error': 'Application not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in ApplicationReviewView: {str(e)}")
            return Response(
                {'error': 'Failed to process application review', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ForwardToFinanceView(APIView):
    """
    Forward department-approved applications to Finance module
    """
    permission_classes = [DepartmentAdminPermission]
    
    @extend_schema(
        summary="Forward Applications to Finance",
        description="Forward department-approved applications to finance module for disbursement processing",
        request=ApplicationForwardSerializer,
        responses={
            200: {'description': 'Applications forwarded successfully'},
            400: {'description': 'Invalid data or applications cannot be forwarded'}
        }
    )
    @transaction.atomic
    def post(self, request):
        """Forward applications to finance module"""
        try:
            user = request.user
            department = user.department_admin_profile.department
            
            serializer = ApplicationForwardSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            application_ids = serializer.validated_data['application_ids']
            forward_remarks = serializer.validated_data.get('forward_remarks', '')
            priority = serializer.validated_data.get('priority', 'medium')
            
            # Get applications that are department-approved
            applications = ScholarshipApplication.objects.filter(
                application_id__in=application_ids,
                student__department=department,
                internal_notes__icontains='DEPT_APPROVED'
            ).exclude(
                internal_notes__icontains='FORWARDED_TO_FINANCE'
            )
            
            if not applications.exists():
                return Response(
                    {'error': 'No eligible applications found for forwarding'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            forwarded_count = 0
            failed_applications = []
            
            for application in applications:
                try:
                    # Create finance forward entry
                    finance_forward = {
                        'action': 'FORWARDED_TO_FINANCE',
                        'forward_remarks': forward_remarks,
                        'priority': priority,
                        'forwarded_by': user.email,
                        'department': department.name,
                        'forwarded_at': timezone.now().isoformat(),
                        'amount_for_disbursement': float(application.amount_approved),
                        'student_details': {
                            'student_id': application.student.student_id,
                            'name': application.student.user.get_full_name(),
                            'email': application.student.user.email,
                            'phone': application.student.user.phone_number,
                            'course': application.student.course_name,
                            'academic_year': application.student.academic_year
                        }
                    }
                    
                    # Update internal notes
                    if application.internal_notes:
                        try:
                            notes_data = json.loads(application.internal_notes)
                            if not isinstance(notes_data, list):
                                notes_data = [notes_data]
                        except (json.JSONDecodeError, TypeError):
                            notes_data = [{'old_notes': application.internal_notes}]
                    else:
                        notes_data = []
                    
                    notes_data.append(finance_forward)
                    application.internal_notes = json.dumps(notes_data, indent=2)
                    
                    # Update application status
                    application.status = 'approved'  # Ready for finance processing
                    application.save()
                    
                    # Send notification to finance module (if API exists)
                    self._notify_finance_module(application, finance_forward)
                    
                    forwarded_count += 1
                    
                except Exception as e:
                    failed_applications.append({
                        'application_id': application.application_id,
                        'error': str(e)
                    })
            
            # Send email notification to finance team
            if forwarded_count > 0:
                self._send_finance_notification_email(department, forwarded_count, user)
            
            return Response({
                'message': f'Successfully forwarded {forwarded_count} applications to finance module',
                'forwarded_count': forwarded_count,
                'failed_applications': failed_applications,
                'priority': priority
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in ForwardToFinanceView: {str(e)}")
            return Response(
                {'error': 'Failed to forward applications', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _notify_finance_module(self, application, finance_forward):
        """Send notification to finance module API"""
        try:
            # This would integrate with the finance module API
            # For now, we'll log the notification
            logger.info(f"Finance notification: Application {application.application_id} forwarded for disbursement")
            
            # Future implementation could make HTTP request to finance API
            # finance_api_url = settings.FINANCE_MODULE_API_URL
            # if finance_api_url:
            #     requests.post(f"{finance_api_url}/notifications/", json=finance_forward)
            
        except Exception as e:
            logger.warning(f"Failed to notify finance module: {str(e)}")
    
    def _send_finance_notification_email(self, department, count, user):
        """Send email notification to finance team"""
        try:
            subject = f"New Applications Forwarded from {department.name}"
            message = f"""
            Dear Finance Team,
            
            {count} scholarship applications have been forwarded from {department.name} department 
            for disbursement processing.
            
            Forwarded by: {user.get_full_name()} ({user.email})
            Department: {department.name}
            Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            Please log into the finance portal to review and process these applications.
            
            Best regards,
            Scholarship Portal System
            """
            
            # Send email to finance team
            finance_emails = getattr(settings, 'FINANCE_TEAM_EMAILS', [])
            if finance_emails:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    finance_emails,
                    fail_silently=True
                )
                
        except Exception as e:
            logger.warning(f"Failed to send finance notification email: {str(e)}")


class DepartmentDashboardView(APIView):
    """
    Department dashboard with key metrics, counts, and analytics
    """
    permission_classes = [DepartmentAdminPermission]
    
    @extend_schema(
        summary="Department Dashboard",
        description="Get comprehensive dashboard data with metrics, counts, and charts for department",
        responses={200: DepartmentDashboardSerializer}
    )
    def get(self, request):
        try:
            user = request.user
            department = user.department_admin_profile.department
            
            # Get cached dashboard data
            cache_key = f"dept_dashboard_{department.id}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                return Response(cached_data, status=status.HTTP_200_OK)
            
            # Generate dashboard data
            dashboard_data = self._generate_dashboard_data(department)
            
            # Cache for 15 minutes
            cache.set(cache_key, dashboard_data, 900)
            
            return Response(dashboard_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in DepartmentDashboardView: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve dashboard data', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_dashboard_data(self, department):
        """Generate comprehensive dashboard data"""
        
        # Base application queryset
        applications = ScholarshipApplication.objects.filter(student__department=department)
        
        # Students in department
        students = Student.objects.filter(department=department)
        
        # Key metrics
        total_students = students.count()
        active_students = students.filter(is_active=True).count()
        verified_students = students.filter(is_verified=True).count()
        
        # Application metrics
        total_applications = applications.count()
        institute_approved = applications.filter(status__in=['approved', 'partially_approved']).count()
        
        # Department review status
        dept_approved = applications.filter(internal_notes__icontains='DEPT_APPROVED').count()
        dept_rejected = applications.filter(internal_notes__icontains='DEPT_REJECTED').count()
        forwarded_to_finance = applications.filter(internal_notes__icontains='FORWARDED_TO_FINANCE').count()
        
        # Pending department review
        pending_dept_review = applications.filter(
            status__in=['approved', 'partially_approved']
        ).exclude(
            Q(internal_notes__icontains='DEPT_APPROVED') | 
            Q(internal_notes__icontains='DEPT_REJECTED')
        ).count()
        
        # Financial metrics
        total_requested = applications.aggregate(Sum('amount_requested'))['amount_requested__sum'] or 0
        total_approved = applications.filter(
            internal_notes__icontains='DEPT_APPROVED'
        ).aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0
        
        # Course-wise breakdown
        course_breakdown = applications.values('student__course_name').annotate(
            count=Count('id'),
            approved_count=Count('id', filter=Q(internal_notes__icontains='DEPT_APPROVED')),
            total_amount=Sum('amount_approved')
        ).order_by('-count')[:5]
        
        # Monthly trends (last 6 months)
        monthly_trends = []
        for i in range(6):
            month_start = (timezone.now().replace(day=1) - timedelta(days=30*i))
            month_end = month_start + timedelta(days=32)
            month_end = month_end.replace(day=1) - timedelta(days=1)
            
            month_apps = applications.filter(
                submitted_at__gte=month_start,
                submitted_at__lte=month_end
            )
            
            monthly_trends.append({
                'month': month_start.strftime('%Y-%m'),
                'total_applications': month_apps.count(),
                'dept_approved': month_apps.filter(internal_notes__icontains='DEPT_APPROVED').count(),
                'forwarded_to_finance': month_apps.filter(internal_notes__icontains='FORWARDED_TO_FINANCE').count(),
                'total_amount': float(month_apps.aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0)
            })
        
        # Scholarship type distribution
        scholarship_types = applications.values('scholarship_type').annotate(
            count=Count('id'),
            dept_approved_count=Count('id', filter=Q(internal_notes__icontains='DEPT_APPROVED')),
            total_amount=Sum('amount_approved')
        ).order_by('-count')
        
        # Priority distribution for pending applications
        priority_distribution = applications.filter(
            status__in=['approved', 'partially_approved']
        ).exclude(
            Q(internal_notes__icontains='DEPT_APPROVED') | 
            Q(internal_notes__icontains='DEPT_REJECTED')
        ).values('priority').annotate(count=Count('id')).order_by('-count')
        
        # Recent activities (last 10 department actions)
        recent_activities = []
        recent_apps = applications.filter(
            Q(internal_notes__icontains='DEPT_APPROVED') | 
            Q(internal_notes__icontains='DEPT_REJECTED') |
            Q(internal_notes__icontains='FORWARDED_TO_FINANCE')
        ).order_by('-updated_at')[:10]
        
        for app in recent_apps:
            if app.internal_notes:
                try:
                    notes_data = json.loads(app.internal_notes)
                    if isinstance(notes_data, list):
                        for note in reversed(notes_data):
                            if isinstance(note, dict) and 'action' in note:
                                if note['action'] in ['DEPT_APPROVED', 'DEPT_REJECTED', 'FORWARDED_TO_FINANCE']:
                                    recent_activities.append({
                                        'application_id': app.application_id,
                                        'student_name': app.student.user.get_full_name(),
                                        'action': note['action'],
                                        'timestamp': note.get('timestamp'),
                                        'amount': float(app.amount_approved or 0)
                                    })
                                    break
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Performance metrics
        avg_processing_time = self._calculate_avg_dept_processing_time(applications)
        
        return {
            'department_name': department.name,
            'department_code': department.code,
            'generated_at': timezone.now(),
            
            # Key metrics
            'key_metrics': {
                'total_students': total_students,
                'active_students': active_students,
                'verified_students': verified_students,
                'verification_rate': (verified_students / total_students * 100) if total_students > 0 else 0,
                'total_applications': total_applications,
                'institute_approved': institute_approved,
                'pending_dept_review': pending_dept_review,
                'dept_approved': dept_approved,
                'dept_rejected': dept_rejected,
                'forwarded_to_finance': forwarded_to_finance,
                'dept_approval_rate': (dept_approved / institute_approved * 100) if institute_approved > 0 else 0,
                'total_amount_requested': float(total_requested),
                'total_amount_approved': float(total_approved),
                'avg_processing_time': avg_processing_time
            },
            
            # Charts and analytics
            'charts': {
                'course_breakdown': list(course_breakdown),
                'monthly_trends': list(reversed(monthly_trends)),
                'scholarship_types': list(scholarship_types),
                'priority_distribution': list(priority_distribution)
            },
            
            # Recent activities
            'recent_activities': recent_activities[:10],
            
            # Alerts and notifications
            'alerts': {
                'pending_review_count': pending_dept_review,
                'high_priority_pending': applications.filter(
                    priority='high',
                    status__in=['approved', 'partially_approved']
                ).exclude(
                    Q(internal_notes__icontains='DEPT_APPROVED') | 
                    Q(internal_notes__icontains='DEPT_REJECTED')
                ).count(),
                'urgent_priority_pending': applications.filter(
                    priority='urgent',
                    status__in=['approved', 'partially_approved']
                ).exclude(
                    Q(internal_notes__icontains='DEPT_APPROVED') | 
                    Q(internal_notes__icontains='DEPT_REJECTED')
                ).count(),
                'overdue_reviews': self._get_overdue_reviews_count(applications)
            }
        }
    
    def _calculate_avg_dept_processing_time(self, applications):
        """Calculate average department processing time"""
        # This would need more detailed tracking of department review times
        # For now, return a placeholder
        return 2.5  # Average days
    
    def _get_overdue_reviews_count(self, applications):
        """Get count of overdue department reviews (>7 days)"""
        seven_days_ago = timezone.now() - timedelta(days=7)
        return applications.filter(
            approved_at__lte=seven_days_ago,
            status__in=['approved', 'partially_approved']
        ).exclude(
            Q(internal_notes__icontains='DEPT_APPROVED') | 
            Q(internal_notes__icontains='DEPT_REJECTED')
        ).count()


class DepartmentReportsView(APIView):
    """
    Generate comprehensive reports for department administrators
    """
    permission_classes = [DepartmentReportsPermission]
    
    @extend_schema(
        summary="Generate Department Reports",
        description="Generate various types of reports for department scholarship management",
        parameters=[
            OpenApiParameter(name='report_type', description='Type of report', required=True, type=str),
            OpenApiParameter(name='date_from', description='Start date for report', required=False, type=str),
            OpenApiParameter(name='date_to', description='End date for report', required=False, type=str),
            OpenApiParameter(name='format', description='Report format (json, csv)', required=False, type=str),
            OpenApiParameter(name='course', description='Filter by course', required=False, type=str),
        ],
        responses={200: DepartmentReportSerializer}
    )
    def get(self, request):
        """Generate and return reports"""
        try:
            user = request.user
            department = user.department_admin_profile.department
            
            # Get report parameters
            report_type = request.query_params.get('report_type', 'summary')
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')
            format_type = request.query_params.get('format', 'json')
            course_filter = request.query_params.get('course')
            
            # Validate report type
            valid_report_types = ['summary', 'detailed', 'financial', 'performance', 'course_wise', 'forwarded_tracking']
            if report_type not in valid_report_types:
                return Response(
                    {'error': f'Invalid report type. Valid types: {", ".join(valid_report_types)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Build base queryset
            queryset = ScholarshipApplication.objects.filter(student__department=department)
            
            # Apply date filtering
            if date_from:
                queryset = queryset.filter(submitted_at__gte=date_from)
            if date_to:
                queryset = queryset.filter(submitted_at__lte=date_to)
            
            # Apply course filtering
            if course_filter:
                queryset = queryset.filter(student__course_name__icontains=course_filter)
            
            # Generate report based on type
            if report_type == 'summary':
                report_data = self._generate_summary_report(queryset, department)
            elif report_type == 'detailed':
                report_data = self._generate_detailed_report(queryset, department)
            elif report_type == 'financial':
                report_data = self._generate_financial_report(queryset, department)
            elif report_type == 'performance':
                report_data = self._generate_performance_report(queryset, department)
            elif report_type == 'course_wise':
                report_data = self._generate_course_wise_report(queryset, department)
            elif report_type == 'forwarded_tracking':
                report_data = self._generate_forwarded_tracking_report(queryset, department)
            
            # Return data in requested format
            if format_type == 'csv':
                return self._export_csv(report_data, report_type)
            else:
                serializer = DepartmentReportSerializer(report_data)
                return Response(serializer.data, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Error in DepartmentReportsView: {str(e)}")
            return Response(
                {'error': 'Failed to generate report', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_summary_report(self, queryset, department):
        """Generate summary report"""
        total_applications = queryset.count()
        
        # Department review status
        dept_approved = queryset.filter(internal_notes__icontains='DEPT_APPROVED').count()
        dept_rejected = queryset.filter(internal_notes__icontains='DEPT_REJECTED').count()
        forwarded_to_finance = queryset.filter(internal_notes__icontains='FORWARDED_TO_FINANCE').count()
        pending_review = queryset.filter(
            status__in=['approved', 'partially_approved']
        ).exclude(
            Q(internal_notes__icontains='DEPT_APPROVED') | 
            Q(internal_notes__icontains='DEPT_REJECTED')
        ).count()
        
        # Financial summary
        total_approved_amount = queryset.filter(
            internal_notes__icontains='DEPT_APPROVED'
        ).aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0
        
        return {
            'report_type': 'summary',
            'department': department.name,
            'generated_at': timezone.now(),
            'total_applications': total_applications,
            'dept_approved': dept_approved,
            'dept_rejected': dept_rejected,
            'forwarded_to_finance': forwarded_to_finance,
            'pending_review': pending_review,
            'approval_rate': (dept_approved / total_applications * 100) if total_applications > 0 else 0,
            'total_approved_amount': float(total_approved_amount),
            'average_approved_amount': float(total_approved_amount / dept_approved) if dept_approved > 0 else 0
        }
    
    def _generate_detailed_report(self, queryset, department):
        """Generate detailed applications report"""
        applications_data = []
        
        for app in queryset.select_related('student', 'student__user'):
            # Determine department status
            dept_status = 'pending_review'
            if app.internal_notes:
                if 'DEPT_APPROVED' in app.internal_notes:
                    dept_status = 'dept_approved'
                elif 'DEPT_REJECTED' in app.internal_notes:
                    dept_status = 'dept_rejected'
                if 'FORWARDED_TO_FINANCE' in app.internal_notes:
                    dept_status = 'forwarded_to_finance'
            
            applications_data.append({
                'application_id': app.application_id,
                'student_id': app.student.student_id,
                'student_name': app.student.user.get_full_name(),
                'course': app.student.course_name,
                'academic_year': app.student.academic_year,
                'scholarship_type': app.scholarship_type,
                'amount_requested': float(app.amount_requested),
                'amount_approved': float(app.amount_approved or 0),
                'institute_status': app.status,
                'dept_status': dept_status,
                'priority': app.priority,
                'submitted_at': app.submitted_at,
                'approved_at': app.approved_at
            })
        
        return {
            'report_type': 'detailed',
            'department': department.name,
            'generated_at': timezone.now(),
            'total_records': len(applications_data),
            'applications': applications_data
        }
    
    def _generate_financial_report(self, queryset, department):
        """Generate financial analysis report"""
        financial_data = {
            'total_requested': float(queryset.aggregate(Sum('amount_requested'))['amount_requested__sum'] or 0),
            'total_approved_by_dept': float(queryset.filter(
                internal_notes__icontains='DEPT_APPROVED'
            ).aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0),
            'total_forwarded': float(queryset.filter(
                internal_notes__icontains='FORWARDED_TO_FINANCE'
            ).aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0)
        }
        
        # Amount ranges analysis
        range_analysis = []
        amount_ranges = [
            {'range': '0-25000', 'min': 0, 'max': 25000},
            {'range': '25001-50000', 'min': 25001, 'max': 50000},
            {'range': '50001-100000', 'min': 50001, 'max': 100000},
            {'range': '100000+', 'min': 100001, 'max': float('inf')}
        ]
        
        for range_data in amount_ranges:
            if range_data['max'] == float('inf'):
                count = queryset.filter(amount_approved__gte=range_data['min']).count()
                total = queryset.filter(amount_approved__gte=range_data['min']).aggregate(
                    Sum('amount_approved'))['amount_approved__sum'] or 0
            else:
                count = queryset.filter(
                    amount_approved__gte=range_data['min'],
                    amount_approved__lte=range_data['max']
                ).count()
                total = queryset.filter(
                    amount_approved__gte=range_data['min'],
                    amount_approved__lte=range_data['max']
                ).aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0
            
            range_analysis.append({
                'range': range_data['range'],
                'count': count,
                'total_amount': float(total)
            })
        
        return {
            'report_type': 'financial',
            'department': department.name,
            'generated_at': timezone.now(),
            'financial_summary': financial_data,
            'amount_range_analysis': range_analysis
        }
    
    def _generate_performance_report(self, queryset, department):
        """Generate performance metrics report"""
        total_apps = queryset.count()
        dept_processed = queryset.filter(
            Q(internal_notes__icontains='DEPT_APPROVED') | 
            Q(internal_notes__icontains='DEPT_REJECTED')
        ).count()
        
        return {
            'report_type': 'performance',
            'department': department.name,
            'generated_at': timezone.now(),
            'processing_efficiency': (dept_processed / total_apps * 100) if total_apps > 0 else 0,
            'total_processed': dept_processed,
            'pending_processing': total_apps - dept_processed,
            'avg_processing_time': 2.5  # Placeholder
        }
    
    def _generate_course_wise_report(self, queryset, department):
        """Generate course-wise analysis report"""
        course_data = queryset.values('student__course_name').annotate(
            total_applications=Count('id'),
            dept_approved=Count('id', filter=Q(internal_notes__icontains='DEPT_APPROVED')),
            dept_rejected=Count('id', filter=Q(internal_notes__icontains='DEPT_REJECTED')),
            forwarded_to_finance=Count('id', filter=Q(internal_notes__icontains='FORWARDED_TO_FINANCE')),
            total_amount_approved=Sum('amount_approved')
        ).order_by('-total_applications')
        
        return {
            'report_type': 'course_wise',
            'department': department.name,
            'generated_at': timezone.now(),
            'course_analysis': list(course_data)
        }
    
    def _generate_forwarded_tracking_report(self, queryset, department):
        """Generate forwarded applications tracking report"""
        forwarded_apps = queryset.filter(internal_notes__icontains='FORWARDED_TO_FINANCE')
        
        tracking_data = []
        for app in forwarded_apps:
            if app.internal_notes:
                try:
                    notes_data = json.loads(app.internal_notes)
                    if isinstance(notes_data, list):
                        for note in notes_data:
                            if isinstance(note, dict) and note.get('action') == 'FORWARDED_TO_FINANCE':
                                tracking_data.append({
                                    'application_id': app.application_id,
                                    'student_name': app.student.user.get_full_name(),
                                    'amount': float(app.amount_approved),
                                    'forwarded_at': note.get('forwarded_at'),
                                    'priority': note.get('priority'),
                                    'forwarded_by': note.get('forwarded_by')
                                })
                                break
                except (json.JSONDecodeError, TypeError):
                    pass
        
        return {
            'report_type': 'forwarded_tracking',
            'department': department.name,
            'generated_at': timezone.now(),
            'total_forwarded': len(tracking_data),
            'forwarded_applications': tracking_data
        }
    
    def _export_csv(self, report_data, report_type):
        """Export report as CSV"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        if report_type == 'detailed' and 'applications' in report_data:
            # Headers
            headers = [
                'Application ID', 'Student ID', 'Student Name', 'Course',
                'Academic Year', 'Scholarship Type', 'Amount Requested',
                'Amount Approved', 'Institute Status', 'Department Status',
                'Priority', 'Submitted At'
            ]
            writer.writerow(headers)
            
            # Data
            for app in report_data['applications']:
                writer.writerow([
                    app['application_id'], app['student_id'], app['student_name'],
                    app['course'], app['academic_year'], app['scholarship_type'],
                    app['amount_requested'], app['amount_approved'],
                    app['institute_status'], app['dept_status'],
                    app['priority'], app['submitted_at']
                ])
        
        # Create HTTP response
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="dept_{report_type}_report_{timezone.now().strftime("%Y%m%d")}.csv"'
        return response
