"""
Finance Module API Views
Comprehensive finance management for scholarship portal
"""

from rest_framework import status, generics, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Sum, Count, Avg, F, Case, When, Value
from django.db.models.functions import TruncMonth, TruncYear, Coalesce
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.shortcuts import get_object_or_404
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
import uuid
import json
import logging

from .models import (
    ScholarshipScheme, ScholarshipDisbursement, FinanceAdmin, 
    Budget, Transaction, FinancialReport
)
from students.models import Student, ScholarshipApplication
from institutes.models import Institute
from departments.models import Department
from .finance_serializers import (
    ScholarshipDisbursementSerializer, DisbursementCreateSerializer,
    FinanceApplicationListSerializer, PaymentStatusUpdateSerializer,
    FinanceReportSerializer, DBTTransferSerializer, FinanceDashboardSerializer,
    ScholarshipCalculationSerializer, BulkPaymentSerializer,
    TransactionSerializer, BudgetSerializer, ScholarshipSchemeSerializer,
    FinanceStatisticsSerializer, DisbursementReportSerializer
)
from .finance_permissions import (
    IsFinanceAdminAuthenticated, CanProcessPaymentsPermission,
    CanGenerateFinanceReportsPermission, CanManageBudgetsPermission,
    FinanceDataAccessPermission
)

logger = logging.getLogger(__name__)


class FinancePagination(PageNumberPagination):
    """Custom pagination for finance module"""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class PendingApplicationsListView(generics.ListAPIView):
    """
    List applications forwarded from departments for finance processing
    """
    permission_classes = [IsFinanceAdminAuthenticated, CanProcessPaymentsPermission]
    serializer_class = FinanceApplicationListSerializer
    pagination_class = FinancePagination
    
    def get_queryset(self):
        """Get applications pending finance processing"""
        finance_admin = getattr(self.request, 'finance_admin', None)
        
        # Base queryset - applications forwarded to finance
        queryset = ScholarshipApplication.objects.filter(
            status__in=['institute_approved', 'dept_approved'],
            internal_notes__icontains='FORWARDED_TO_FINANCE'
        ).select_related(
            'student', 'student__user', 'student__institute', 'student__department'
        ).exclude(
            disbursement__isnull=False  # Exclude already disbursed
        )
        
        # Filter by institute if admin is institute-specific
        if finance_admin and finance_admin.institute:
            queryset = queryset.filter(student__institute=finance_admin.institute)
        
        # Apply filters from query parameters
        filters = {}
        
        # Date range filter
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            filters['submitted_at__gte'] = start_date
        if end_date:
            filters['submitted_at__lte'] = end_date
        
        # Amount range filter
        min_amount = self.request.query_params.get('min_amount')
        max_amount = self.request.query_params.get('max_amount')
        if min_amount:
            filters['amount_approved__gte'] = min_amount
        if max_amount:
            filters['amount_approved__lte'] = max_amount
        
        # Institute filter (for system admin)
        institute_id = self.request.query_params.get('institute')
        if institute_id:
            filters['student__institute_id'] = institute_id
        
        # Department filter
        department_id = self.request.query_params.get('department')
        if department_id:
            filters['student__department_id'] = department_id
        
        # Priority filter
        priority = self.request.query_params.get('priority')
        if priority:
            filters['priority'] = priority
        
        # Scholarship type filter
        scholarship_type = self.request.query_params.get('scholarship_type')
        if scholarship_type:
            filters['scholarship_type'] = scholarship_type
        
        # Apply filters
        if filters:
            queryset = queryset.filter(**filters)
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(application_id__icontains=search) |
                Q(student__student_id__icontains=search) |
                Q(student__user__first_name__icontains=search) |
                Q(student__user__last_name__icontains=search) |
                Q(student__user__email__icontains=search) |
                Q(scholarship_name__icontains=search)
            )
        
        # Sorting
        sort_by = self.request.query_params.get('sort_by', '-submitted_at')
        if sort_by in [
            'submitted_at', '-submitted_at', 'amount_approved', '-amount_approved',
            'priority', '-priority', 'student__user__last_name', '-student__user__last_name'
        ]:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-submitted_at')
        
        return queryset.distinct()
    
    def list(self, request, *args, **kwargs):
        """Override list to add summary statistics"""
        try:
            queryset = self.get_queryset()
            
            # Calculate summary statistics
            stats = queryset.aggregate(
                total_count=Count('id'),
                total_amount=Coalesce(Sum('amount_approved'), 0),
                avg_amount=Coalesce(Avg('amount_approved'), 0),
                urgent_count=Count('id', filter=Q(priority='urgent')),
                high_count=Count('id', filter=Q(priority='high'))
            )
            
            # Get paginated response
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                result = self.get_paginated_response(serializer.data)
                result.data['summary'] = stats
                return result
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'results': serializer.data,
                'summary': stats
            })
            
        except Exception as e:
            logger.error(f"Error in PendingApplicationsListView: {str(e)}")
            return Response(
                {'error': 'Failed to fetch pending applications'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ScholarshipCalculationView(views.APIView):
    """
    Calculate scholarship amount based on various parameters
    """
    permission_classes = [IsFinanceAdminAuthenticated, CanProcessPaymentsPermission]
    
    def post(self, request):
        """Calculate scholarship amount for an application"""
        try:
            serializer = ScholarshipCalculationSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Invalid input data', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            application_id = serializer.validated_data['application_id']
            calculation_type = serializer.validated_data.get('calculation_type', 'standard')
            custom_factors = serializer.validated_data.get('custom_factors', {})
            
            # Get application
            try:
                application = ScholarshipApplication.objects.select_related(
                    'student', 'student__user', 'student__institute', 'student__department'
                ).get(application_id=application_id)
            except ScholarshipApplication.DoesNotExist:
                return Response(
                    {'error': 'Application not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check access permissions
            finance_admin = getattr(request, 'finance_admin', None)
            if finance_admin and finance_admin.institute:
                if application.student.institute != finance_admin.institute:
                    return Response(
                        {'error': 'Access denied'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Calculate scholarship amount
            calculation_result = self._calculate_scholarship_amount(
                application, calculation_type, custom_factors
            )
            
            return Response(calculation_result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in scholarship calculation: {str(e)}")
            return Response(
                {'error': 'Calculation failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_scholarship_amount(self, application, calculation_type, custom_factors):
        """
        Calculate scholarship amount based on various factors
        """
        student = application.student
        base_amount = float(application.amount_approved or application.amount_requested)
        
        calculation_factors = {
            'base_amount': base_amount,
            'student_cgpa': float(student.cgpa or 0),
            'family_income': custom_factors.get('family_income', 0),
            'course_level': student.course_level,
            'scholarship_type': application.scholarship_type,
            'academic_year': student.academic_year,
            'state_category': custom_factors.get('state_category', 'general'),
            'rural_urban': custom_factors.get('rural_urban', 'urban')
        }
        
        calculated_amounts = {}
        
        if calculation_type == 'standard':
            # Standard calculation based on CGPA and course level
            calculated_amounts = self._standard_calculation(calculation_factors)
        elif calculation_type == 'need_based':
            # Need-based calculation considering family income
            calculated_amounts = self._need_based_calculation(calculation_factors)
        elif calculation_type == 'merit_based':
            # Merit-based calculation focusing on academic performance
            calculated_amounts = self._merit_based_calculation(calculation_factors)
        elif calculation_type == 'government_scheme':
            # Government scheme calculation with standardized amounts
            calculated_amounts = self._government_scheme_calculation(calculation_factors)
        else:
            # Custom calculation
            calculated_amounts = self._custom_calculation(calculation_factors, custom_factors)
        
        # Calculate breakdown components
        breakdown = self._calculate_breakdown(calculated_amounts['final_amount'], student)
        
        return {
            'application_id': application.application_id,
            'student_name': student.user.get_full_name(),
            'calculation_type': calculation_type,
            'calculation_factors': calculation_factors,
            'calculated_amounts': calculated_amounts,
            'breakdown': breakdown,
            'recommendations': self._get_recommendations(calculation_factors, calculated_amounts),
            'calculated_at': timezone.now().isoformat()
        }
    
    def _standard_calculation(self, factors):
        """Standard scholarship calculation"""
        base_amount = factors['base_amount']
        cgpa = factors['student_cgpa']
        course_level = factors['course_level']
        
        # CGPA multiplier
        if cgpa >= 9.0:
            cgpa_multiplier = 1.2
        elif cgpa >= 8.0:
            cgpa_multiplier = 1.1
        elif cgpa >= 7.0:
            cgpa_multiplier = 1.0
        elif cgpa >= 6.0:
            cgpa_multiplier = 0.9
        else:
            cgpa_multiplier = 0.8
        
        # Course level multiplier
        course_multipliers = {
            'undergraduate': 1.0,
            'postgraduate': 1.2,
            'doctoral': 1.5,
            'diploma': 0.8
        }
        course_multiplier = course_multipliers.get(course_level, 1.0)
        
        calculated_amount = base_amount * cgpa_multiplier * course_multiplier
        
        return {
            'base_amount': base_amount,
            'cgpa_multiplier': cgpa_multiplier,
            'course_multiplier': course_multiplier,
            'calculated_amount': round(calculated_amount, 2),
            'final_amount': round(calculated_amount, 2)
        }
    
    def _need_based_calculation(self, factors):
        """Need-based scholarship calculation"""
        base_amount = factors['base_amount']
        family_income = factors['family_income']
        course_level = factors['course_level']
        
        # Income-based multiplier
        if family_income <= 100000:
            income_multiplier = 1.5
        elif family_income <= 200000:
            income_multiplier = 1.3
        elif family_income <= 400000:
            income_multiplier = 1.1
        elif family_income <= 600000:
            income_multiplier = 0.9
        else:
            income_multiplier = 0.7
        
        # Course level adjustment
        course_adjustments = {
            'undergraduate': 1.0,
            'postgraduate': 1.1,
            'doctoral': 1.2,
            'diploma': 0.9
        }
        course_adjustment = course_adjustments.get(course_level, 1.0)
        
        calculated_amount = base_amount * income_multiplier * course_adjustment
        
        return {
            'base_amount': base_amount,
            'family_income': family_income,
            'income_multiplier': income_multiplier,
            'course_adjustment': course_adjustment,
            'calculated_amount': round(calculated_amount, 2),
            'final_amount': round(calculated_amount, 2)
        }
    
    def _merit_based_calculation(self, factors):
        """Merit-based scholarship calculation"""
        base_amount = factors['base_amount']
        cgpa = factors['student_cgpa']
        scholarship_type = factors['scholarship_type']
        
        # High merit multiplier
        if cgpa >= 9.5:
            merit_multiplier = 1.5
        elif cgpa >= 9.0:
            merit_multiplier = 1.3
        elif cgpa >= 8.5:
            merit_multiplier = 1.2
        elif cgpa >= 8.0:
            merit_multiplier = 1.1
        else:
            merit_multiplier = 1.0
        
        # Type-specific bonus
        type_bonuses = {
            'research': 1.2,
            'sports': 1.1,
            'arts': 1.1,
            'merit': 1.0
        }
        type_bonus = type_bonuses.get(scholarship_type, 1.0)
        
        calculated_amount = base_amount * merit_multiplier * type_bonus
        
        return {
            'base_amount': base_amount,
            'cgpa': cgpa,
            'merit_multiplier': merit_multiplier,
            'type_bonus': type_bonus,
            'calculated_amount': round(calculated_amount, 2),
            'final_amount': round(calculated_amount, 2)
        }
    
    def _government_scheme_calculation(self, factors):
        """Government scheme standardized calculation"""
        course_level = factors['course_level']
        state_category = factors['state_category']
        rural_urban = factors['rural_urban']
        
        # Government scheme base amounts
        base_amounts = {
            'undergraduate': 30000,
            'postgraduate': 40000,
            'doctoral': 60000,
            'diploma': 20000
        }
        
        base_amount = base_amounts.get(course_level, 30000)
        
        # Category adjustments
        category_multipliers = {
            'sc': 1.2,
            'st': 1.2,
            'obc': 1.1,
            'general': 1.0,
            'minority': 1.15
        }
        category_multiplier = category_multipliers.get(state_category, 1.0)
        
        # Rural/Urban adjustment
        location_multiplier = 1.1 if rural_urban == 'rural' else 1.0
        
        calculated_amount = base_amount * category_multiplier * location_multiplier
        
        return {
            'scheme_base_amount': base_amount,
            'category': state_category,
            'category_multiplier': category_multiplier,
            'location': rural_urban,
            'location_multiplier': location_multiplier,
            'calculated_amount': round(calculated_amount, 2),
            'final_amount': round(calculated_amount, 2)
        }
    
    def _custom_calculation(self, factors, custom_factors):
        """Custom calculation with user-defined parameters"""
        base_amount = factors['base_amount']
        
        # Apply custom multipliers
        multipliers = custom_factors.get('multipliers', {})
        total_multiplier = 1.0
        
        for key, value in multipliers.items():
            if isinstance(value, (int, float)) and 0.1 <= value <= 5.0:
                total_multiplier *= value
        
        # Apply custom adjustments
        adjustments = custom_factors.get('adjustments', {})
        total_adjustment = 0
        
        for key, value in adjustments.items():
            if isinstance(value, (int, float)) and -50000 <= value <= 50000:
                total_adjustment += value
        
        calculated_amount = (base_amount * total_multiplier) + total_adjustment
        
        return {
            'base_amount': base_amount,
            'custom_multipliers': multipliers,
            'total_multiplier': round(total_multiplier, 3),
            'custom_adjustments': adjustments,
            'total_adjustment': total_adjustment,
            'calculated_amount': round(calculated_amount, 2),
            'final_amount': round(max(calculated_amount, 0), 2)  # Ensure non-negative
        }
    
    def _calculate_breakdown(self, total_amount, student):
        """Calculate breakdown of scholarship amount"""
        # Standard breakdown percentages
        tuition_percentage = 0.7  # 70% for tuition
        maintenance_percentage = 0.25  # 25% for maintenance
        books_percentage = 0.05  # 5% for books and materials
        
        tuition_amount = total_amount * tuition_percentage
        maintenance_amount = total_amount * maintenance_percentage
        books_amount = total_amount * books_percentage
        
        return {
            'total_amount': round(total_amount, 2),
            'tuition_fee': round(tuition_amount, 2),
            'maintenance_allowance': round(maintenance_amount, 2),
            'books_and_materials': round(books_amount, 2),
            'breakdown_percentages': {
                'tuition': tuition_percentage * 100,
                'maintenance': maintenance_percentage * 100,
                'books': books_percentage * 100
            }
        }
    
    def _get_recommendations(self, factors, amounts):
        """Get recommendations based on calculation"""
        recommendations = []
        
        final_amount = amounts['final_amount']
        base_amount = factors['base_amount']
        
        if final_amount > base_amount * 1.2:
            recommendations.append({
                'type': 'warning',
                'message': 'Calculated amount significantly exceeds requested amount',
                'suggestion': 'Review calculation parameters'
            })
        
        if final_amount < base_amount * 0.5:
            recommendations.append({
                'type': 'info',
                'message': 'Calculated amount is much lower than requested',
                'suggestion': 'Consider need-based calculation'
            })
        
        if factors['student_cgpa'] >= 9.0:
            recommendations.append({
                'type': 'success',
                'message': 'Excellent academic performance',
                'suggestion': 'Consider merit-based enhancement'
            })
        
        return recommendations


class PaymentStatusUpdateView(views.APIView):
    """
    Update payment status for scholarship disbursements
    Mark tuition fee and maintenance allowance as paid
    """
    permission_classes = [IsFinanceAdminAuthenticated, CanProcessPaymentsPermission]
    
    def post(self, request):
        """Update payment status for single or multiple disbursements"""
        try:
            serializer = PaymentStatusUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Invalid input data', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            disbursement_ids = serializer.validated_data['disbursement_ids']
            payment_status = serializer.validated_data['payment_status']
            payment_components = serializer.validated_data.get('payment_components', [])
            payment_remarks = serializer.validated_data.get('payment_remarks', '')
            
            results = []
            finance_admin = getattr(request, 'finance_admin', None)
            
            with transaction.atomic():
                for disbursement_id in disbursement_ids:
                    try:
                        disbursement = ScholarshipDisbursement.objects.select_related(
                            'application', 'application__student'
                        ).get(disbursement_id=disbursement_id)
                        
                        # Check access permissions
                        if finance_admin and finance_admin.institute:
                            if disbursement.application.student.institute != finance_admin.institute:
                                results.append({
                                    'disbursement_id': disbursement_id,
                                    'status': 'error',
                                    'message': 'Access denied'
                                })
                                continue
                        
                        # Update payment status
                        update_result = self._update_payment_status(
                            disbursement, payment_status, payment_components, payment_remarks, request.user
                        )
                        
                        results.append({
                            'disbursement_id': disbursement_id,
                            'status': 'success',
                            'message': 'Payment status updated successfully',
                            'details': update_result
                        })
                        
                    except ScholarshipDisbursement.DoesNotExist:
                        results.append({
                            'disbursement_id': disbursement_id,
                            'status': 'error',
                            'message': 'Disbursement not found'
                        })
                    except Exception as e:
                        logger.error(f"Error updating disbursement {disbursement_id}: {str(e)}")
                        results.append({
                            'disbursement_id': disbursement_id,
                            'status': 'error',
                            'message': f'Update failed: {str(e)}'
                        })
            
            # Calculate summary
            success_count = len([r for r in results if r['status'] == 'success'])
            error_count = len([r for r in results if r['status'] == 'error'])
            
            return Response({
                'message': f'Processed {len(disbursement_ids)} disbursements',
                'summary': {
                    'total': len(disbursement_ids),
                    'success': success_count,
                    'errors': error_count
                },
                'results': results
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in PaymentStatusUpdateView: {str(e)}")
            return Response(
                {'error': 'Payment status update failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _update_payment_status(self, disbursement, payment_status, payment_components, remarks, user):
        """Update payment status for a disbursement"""
        # Update disbursement status
        disbursement.status = payment_status
        disbursement.remarks = f"{disbursement.remarks or ''}\n{remarks}".strip()
        disbursement.updated_at = timezone.now()
        
        if payment_status in ['disbursed', 'completed']:
            disbursement.disbursed_by = user
            disbursement.disbursement_date = timezone.now()
        
        disbursement.save()
        
        # Create payment component records (if specified)
        component_updates = []
        if payment_components:
            for component in payment_components:
                component_type = component.get('type')  # 'tuition', 'maintenance', 'books'
                amount = component.get('amount', 0)
                is_paid = component.get('is_paid', True)
                
                component_updates.append({
                    'type': component_type,
                    'amount': amount,
                    'is_paid': is_paid,
                    'paid_date': timezone.now() if is_paid else None
                })
        
        # Update application status if payment is complete
        application = disbursement.application
        if payment_status == 'disbursed':
            application.status = 'disbursed'
            application.save()
        elif payment_status == 'completed':
            application.status = 'completed'
            application.save()
        
        # Create transaction record
        self._create_payment_transaction(disbursement, payment_status, component_updates, user)
        
        return {
            'disbursement_status': payment_status,
            'application_status': application.status,
            'payment_components': component_updates,
            'disbursement_date': disbursement.disbursement_date,
            'updated_at': disbursement.updated_at
        }
    
    def _create_payment_transaction(self, disbursement, payment_status, components, user):
        """Create transaction record for payment"""
        transaction_id = f"TXN{timezone.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
        
        # Create main transaction
        Transaction.objects.create(
            transaction_id=transaction_id,
            institute=disbursement.application.student.institute,
            transaction_type='debit',
            category='scholarship_disbursement',
            amount=disbursement.amount,
            description=f"Scholarship payment - {disbursement.disbursement_id}",
            reference_number=disbursement.disbursement_id,
            student=disbursement.application.student,
            disbursement=disbursement,
            processed_by=user,
            transaction_date=timezone.now()
        )
        
        # Create component-wise transactions if specified
        for component in components:
            if component['is_paid']:
                component_txn_id = f"TXN{timezone.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
                Transaction.objects.create(
                    transaction_id=component_txn_id,
                    institute=disbursement.application.student.institute,
                    transaction_type='debit',
                    category='scholarship_disbursement',
                    amount=component['amount'],
                    description=f"Scholarship {component['type']} payment - {disbursement.disbursement_id}",
                    reference_number=disbursement.disbursement_id,
                    student=disbursement.application.student,
                    disbursement=disbursement,
                    processed_by=user,
                    transaction_date=timezone.now()
                )


class DBTTransferSimulationView(views.APIView):
    """
    Simulate DBT (Direct Benefit Transfer) to student bank accounts
    """
    permission_classes = [IsFinanceAdminAuthenticated, CanProcessPaymentsPermission]
    
    def post(self, request):
        """Simulate DBT transfer for disbursements"""
        try:
            serializer = DBTTransferSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Invalid input data', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            disbursement_ids = serializer.validated_data['disbursement_ids']
            transfer_batch_id = f"DBT{timezone.now().strftime('%Y%m%d%H%M')}{str(uuid.uuid4())[:6].upper()}"
            
            results = []
            total_amount = Decimal('0')
            finance_admin = getattr(request, 'finance_admin', None)
            
            with transaction.atomic():
                for disbursement_id in disbursement_ids:
                    try:
                        disbursement = ScholarshipDisbursement.objects.select_related(
                            'application', 'application__student', 'application__student__user'
                        ).get(disbursement_id=disbursement_id)
                        
                        # Check access permissions
                        if finance_admin and finance_admin.institute:
                            if disbursement.application.student.institute != finance_admin.institute:
                                results.append({
                                    'disbursement_id': disbursement_id,
                                    'status': 'error',
                                    'message': 'Access denied'
                                })
                                continue
                        
                        # Simulate DBT transfer
                        transfer_result = self._simulate_dbt_transfer(
                            disbursement, transfer_batch_id, request.user
                        )
                        
                        if transfer_result['success']:
                            total_amount += disbursement.amount
                            results.append({
                                'disbursement_id': disbursement_id,
                                'status': 'success',
                                'message': 'DBT transfer simulated successfully',
                                'details': transfer_result
                            })
                        else:
                            results.append({
                                'disbursement_id': disbursement_id,
                                'status': 'failed',
                                'message': transfer_result.get('error', 'Transfer failed'),
                                'details': transfer_result
                            })
                        
                    except ScholarshipDisbursement.DoesNotExist:
                        results.append({
                            'disbursement_id': disbursement_id,
                            'status': 'error',
                            'message': 'Disbursement not found'
                        })
                    except Exception as e:
                        logger.error(f"Error in DBT transfer {disbursement_id}: {str(e)}")
                        results.append({
                            'disbursement_id': disbursement_id,
                            'status': 'error',
                            'message': f'Transfer failed: {str(e)}'
                        })
            
            # Calculate summary
            success_count = len([r for r in results if r['status'] == 'success'])
            failed_count = len([r for r in results if r['status'] == 'failed'])
            error_count = len([r for r in results if r['status'] == 'error'])
            
            return Response({
                'transfer_batch_id': transfer_batch_id,
                'message': f'DBT transfer simulation completed for {len(disbursement_ids)} disbursements',
                'summary': {
                    'total_transfers': len(disbursement_ids),
                    'successful': success_count,
                    'failed': failed_count,
                    'errors': error_count,
                    'total_amount': float(total_amount)
                },
                'results': results,
                'processed_at': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in DBT transfer simulation: {str(e)}")
            return Response(
                {'error': 'DBT transfer simulation failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _simulate_dbt_transfer(self, disbursement, batch_id, user):
        """Simulate DBT transfer for a single disbursement"""
        student = disbursement.application.student
        
        # Validate bank details
        if not disbursement.bank_account_number or not disbursement.bank_ifsc:
            return {
                'success': False,
                'error': 'Incomplete bank details',
                'bank_validation': False
            }
        
        # Simulate transfer processing time (1-3 seconds)
        import time
        import random
        processing_time = random.uniform(1, 3)
        time.sleep(0.1)  # Small delay for realism
        
        # Simulate success/failure (95% success rate)
        transfer_success = random.random() < 0.95
        
        if transfer_success:
            # Generate transaction reference
            transaction_ref = f"DBT{timezone.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            
            # Update disbursement record
            disbursement.status = 'disbursed'
            disbursement.transaction_reference = transaction_ref
            disbursement.disbursement_date = timezone.now()
            disbursement.disbursed_by = user
            disbursement.remarks = f"{disbursement.remarks or ''}\nDBT Transfer - Batch: {batch_id}".strip()
            disbursement.save()
            
            # Update application status
            application = disbursement.application
            application.status = 'disbursed'
            application.save()
            
            # Create transaction record
            Transaction.objects.create(
                transaction_id=f"DBT{timezone.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}",
                institute=student.institute,
                transaction_type='debit',
                category='scholarship_disbursement',
                amount=disbursement.amount,
                description=f"DBT Transfer - {disbursement.disbursement_id}",
                reference_number=transaction_ref,
                student=student,
                disbursement=disbursement,
                processed_by=user,
                transaction_date=timezone.now()
            )
            
            return {
                'success': True,
                'transaction_reference': transaction_ref,
                'transfer_batch_id': batch_id,
                'amount': float(disbursement.amount),
                'bank_account': f"****{disbursement.bank_account_number[-4:]}",
                'bank_ifsc': disbursement.bank_ifsc,
                'student_name': student.user.get_full_name(),
                'student_id': student.student_id,
                'transfer_date': disbursement.disbursement_date.isoformat(),
                'processing_time': round(processing_time, 2),
                'bank_validation': True,
                'transfer_status': 'completed'
            }
        else:
            # Simulate transfer failure
            failure_reasons = [
                'Invalid bank account number',
                'Bank server temporarily unavailable',
                'Insufficient funds in source account',
                'Account frozen by bank',
                'IFSC code mismatch'
            ]
            failure_reason = random.choice(failure_reasons)
            
            # Update disbursement with failure
            disbursement.status = 'failed'
            disbursement.remarks = f"{disbursement.remarks or ''}\nDBT Transfer Failed: {failure_reason}".strip()
            disbursement.save()
            
            return {
                'success': False,
                'error': failure_reason,
                'transfer_batch_id': batch_id,
                'amount': float(disbursement.amount),
                'bank_account': f"****{disbursement.bank_account_number[-4:]}",
                'bank_ifsc': disbursement.bank_ifsc,
                'student_name': student.user.get_full_name(),
                'student_id': student.student_id,
                'processing_time': round(processing_time, 2),
                'bank_validation': False,
                'transfer_status': 'failed',
                'retry_possible': True
            }


class FinanceReportsView(views.APIView):
    """
    Generate comprehensive finance reports
    """
    permission_classes = [IsFinanceAdminAuthenticated, CanGenerateFinanceReportsPermission]
    
    def get(self, request, report_type):
        """Generate and return finance reports"""
        try:
            # Validate report type
            valid_report_types = [
                'disbursement_summary', 'budget_utilization', 'transaction_report',
                'institute_financial', 'scholarship_analytics', 'payment_status'
            ]
            
            if report_type not in valid_report_types:
                return Response(
                    {'error': f'Invalid report type. Valid types: {valid_report_types}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get query parameters
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            institute_id = request.query_params.get('institute')
            format_type = request.query_params.get('format', 'json')
            
            # Default date range (last 3 months)
            if not end_date:
                end_date = timezone.now().date()
            else:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if not start_date:
                start_date = end_date - timedelta(days=90)
            else:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
            # Check access permissions
            finance_admin = getattr(request, 'finance_admin', None)
            if finance_admin and finance_admin.institute and not institute_id:
                institute_id = finance_admin.institute.id
            
            # Generate report based on type
            if report_type == 'disbursement_summary':
                report_data = self._generate_disbursement_summary(start_date, end_date, institute_id)
            elif report_type == 'budget_utilization':
                report_data = self._generate_budget_utilization_report(start_date, end_date, institute_id)
            elif report_type == 'transaction_report':
                report_data = self._generate_transaction_report(start_date, end_date, institute_id)
            elif report_type == 'institute_financial':
                report_data = self._generate_institute_financial_report(start_date, end_date, institute_id)
            elif report_type == 'scholarship_analytics':
                report_data = self._generate_scholarship_analytics(start_date, end_date, institute_id)
            elif report_type == 'payment_status':
                report_data = self._generate_payment_status_report(start_date, end_date, institute_id)
            
            # Add metadata
            report_data.update({
                'report_metadata': {
                    'report_type': report_type,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'generated_at': timezone.now().isoformat(),
                    'generated_by': request.user.get_full_name(),
                    'institute_filter': institute_id
                }
            })
            
            # Handle export formats
            if format_type == 'excel':
                return self._export_to_excel(report_data, report_type)
            elif format_type == 'pdf':
                return self._export_to_pdf(report_data, report_type)
            else:
                serializer = FinanceReportSerializer(report_data)
                return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error generating finance report: {str(e)}")
            return Response(
                {'error': 'Report generation failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_disbursement_summary(self, start_date, end_date, institute_id):
        """Generate disbursement summary report"""
        filters = {
            'created_at__date__gte': start_date,
            'created_at__date__lte': end_date
        }
        
        if institute_id:
            filters['application__student__institute_id'] = institute_id
        
        disbursements = ScholarshipDisbursement.objects.filter(**filters)
        
        # Summary statistics
        summary = disbursements.aggregate(
            total_disbursements=Count('id'),
            total_amount=Coalesce(Sum('amount'), 0),
            avg_amount=Coalesce(Avg('amount'), 0),
            pending_count=Count('id', filter=Q(status='pending')),
            processing_count=Count('id', filter=Q(status='processing')),
            disbursed_count=Count('id', filter=Q(status='disbursed')),
            failed_count=Count('id', filter=Q(status='failed')),
            cancelled_count=Count('id', filter=Q(status='cancelled'))
        )
        
        # Status-wise breakdown
        status_breakdown = list(disbursements.values('status').annotate(
            count=Count('id'),
            total_amount=Coalesce(Sum('amount'), 0)
        ).order_by('status'))
        
        # Method-wise breakdown
        method_breakdown = list(disbursements.values('disbursement_method').annotate(
            count=Count('id'),
            total_amount=Coalesce(Sum('amount'), 0)
        ).order_by('disbursement_method'))
        
        # Monthly trend
        monthly_trend = list(disbursements.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id'),
            total_amount=Coalesce(Sum('amount'), 0)
        ).order_by('month'))
        
        # Institute-wise breakdown (if not filtered by institute)
        institute_breakdown = []
        if not institute_id:
            institute_breakdown = list(disbursements.values(
                'application__student__institute__name'
            ).annotate(
                count=Count('id'),
                total_amount=Coalesce(Sum('amount'), 0)
            ).order_by('-total_amount'))
        
        return {
            'report_type': 'disbursement_summary',
            'summary': summary,
            'status_breakdown': status_breakdown,
            'method_breakdown': method_breakdown,
            'monthly_trend': monthly_trend,
            'institute_breakdown': institute_breakdown
        }
    
    def _generate_budget_utilization_report(self, start_date, end_date, institute_id):
        """Generate budget utilization report"""
        filters = {'is_active': True}
        
        if institute_id:
            filters['institute_id'] = institute_id
        
        budgets = Budget.objects.filter(**filters)
        
        # Calculate utilization
        budget_data = []
        total_budget = Decimal('0')
        total_utilized = Decimal('0')
        
        for budget in budgets:
            # Get transactions for this budget in date range
            budget_transactions = Transaction.objects.filter(
                budget=budget,
                transaction_date__date__gte=start_date,
                transaction_date__date__lte=end_date
            ).aggregate(
                period_utilization=Coalesce(Sum('amount'), 0)
            )
            
            utilization_percentage = 0
            if budget.total_amount > 0:
                utilization_percentage = (budget.utilized_amount / budget.total_amount) * 100
            
            budget_data.append({
                'budget_name': budget.name,
                'budget_type': budget.budget_type,
                'total_amount': float(budget.total_amount),
                'utilized_amount': float(budget.utilized_amount),
                'remaining_amount': float(budget.remaining_amount),
                'period_utilization': float(budget_transactions['period_utilization']),
                'utilization_percentage': round(utilization_percentage, 2),
                'financial_year': budget.financial_year
            })
            
            total_budget += budget.total_amount
            total_utilized += budget.utilized_amount
        
        overall_utilization = 0
        if total_budget > 0:
            overall_utilization = (total_utilized / total_budget) * 100
        
        return {
            'report_type': 'budget_utilization',
            'overall_summary': {
                'total_budget': float(total_budget),
                'total_utilized': float(total_utilized),
                'total_remaining': float(total_budget - total_utilized),
                'overall_utilization_percentage': round(overall_utilization, 2)
            },
            'budget_details': budget_data
        }
    
    def _generate_transaction_report(self, start_date, end_date, institute_id):
        """Generate transaction report"""
        filters = {
            'transaction_date__date__gte': start_date,
            'transaction_date__date__lte': end_date
        }
        
        if institute_id:
            filters['institute_id'] = institute_id
        
        transactions = Transaction.objects.filter(**filters)
        
        # Summary statistics
        summary = transactions.aggregate(
            total_transactions=Count('id'),
            total_credit=Coalesce(Sum('amount', filter=Q(transaction_type='credit')), 0),
            total_debit=Coalesce(Sum('amount', filter=Q(transaction_type='debit')), 0),
            net_amount=Coalesce(Sum('amount', filter=Q(transaction_type='credit')), 0) - 
                      Coalesce(Sum('amount', filter=Q(transaction_type='debit')), 0)
        )
        
        # Category-wise breakdown
        category_breakdown = list(transactions.values('category').annotate(
            count=Count('id'),
            total_amount=Coalesce(Sum('amount'), 0)
        ).order_by('-total_amount'))
        
        # Daily trend
        daily_trend = list(transactions.extra(
            select={'day': 'DATE(transaction_date)'}
        ).values('day').annotate(
            count=Count('id'),
            credit_amount=Coalesce(Sum('amount', filter=Q(transaction_type='credit')), 0),
            debit_amount=Coalesce(Sum('amount', filter=Q(transaction_type='debit')), 0)
        ).order_by('day'))
        
        return {
            'report_type': 'transaction_report',
            'summary': summary,
            'category_breakdown': category_breakdown,
            'daily_trend': daily_trend
        }
    
    def _generate_institute_financial_report(self, start_date, end_date, institute_id):
        """Generate institute financial summary"""
        filters = {}
        if institute_id:
            filters['student__institute_id'] = institute_id
        
        # Scholarship applications in period
        applications = ScholarshipApplication.objects.filter(
            submitted_at__date__gte=start_date,
            submitted_at__date__lte=end_date,
            **filters
        )
        
        app_summary = applications.aggregate(
            total_applications=Count('id'),
            total_requested=Coalesce(Sum('amount_requested'), 0),
            total_approved=Coalesce(Sum('amount_approved'), 0),
            approved_count=Count('id', filter=Q(status__in=['approved', 'disbursed', 'completed']))
        )
        
        # Disbursements in period
        disbursement_filters = {
            'created_at__date__gte': start_date,
            'created_at__date__lte': end_date
        }
        if institute_id:
            disbursement_filters['application__student__institute_id'] = institute_id
        
        disbursements = ScholarshipDisbursement.objects.filter(**disbursement_filters)
        
        disb_summary = disbursements.aggregate(
            total_disbursements=Count('id'),
            total_disbursed_amount=Coalesce(Sum('amount'), 0),
            successful_disbursements=Count('id', filter=Q(status='disbursed'))
        )
        
        return {
            'report_type': 'institute_financial',
            'period': f"{start_date} to {end_date}",
            'application_summary': app_summary,
            'disbursement_summary': disb_summary,
            'financial_efficiency': {
                'approval_rate': round(
                    (app_summary['approved_count'] / app_summary['total_applications'] * 100) 
                    if app_summary['total_applications'] > 0 else 0, 2
                ),
                'disbursement_rate': round(
                    (disb_summary['successful_disbursements'] / disb_summary['total_disbursements'] * 100)
                    if disb_summary['total_disbursements'] > 0 else 0, 2
                )
            }
        }
    
    def _generate_scholarship_analytics(self, start_date, end_date, institute_id):
        """Generate scholarship analytics report"""
        filters = {
            'submitted_at__date__gte': start_date,
            'submitted_at__date__lte': end_date
        }
        
        if institute_id:
            filters['student__institute_id'] = institute_id
        
        applications = ScholarshipApplication.objects.filter(**filters)
        
        # Type-wise analysis
        type_analysis = list(applications.values('scholarship_type').annotate(
            count=Count('id'),
            total_requested=Coalesce(Sum('amount_requested'), 0),
            total_approved=Coalesce(Sum('amount_approved'), 0),
            avg_amount=Coalesce(Avg('amount_approved'), 0)
        ).order_by('-count'))
        
        # Status distribution
        status_distribution = list(applications.values('status').annotate(
            count=Count('id'),
            percentage=Count('id') * 100.0 / applications.count() if applications.count() > 0 else 0
        ).order_by('-count'))
        
        # Department-wise analysis
        dept_analysis = list(applications.values(
            'student__department__name'
        ).annotate(
            count=Count('id'),
            total_approved=Coalesce(Sum('amount_approved'), 0)
        ).order_by('-count'))
        
        return {
            'report_type': 'scholarship_analytics',
            'type_wise_analysis': type_analysis,
            'status_distribution': status_distribution,
            'department_wise_analysis': dept_analysis
        }
    
    def _generate_payment_status_report(self, start_date, end_date, institute_id):
        """Generate payment status report"""
        filters = {
            'created_at__date__gte': start_date,
            'created_at__date__lte': end_date
        }
        
        if institute_id:
            filters['application__student__institute_id'] = institute_id
        
        disbursements = ScholarshipDisbursement.objects.filter(**filters).select_related(
            'application', 'application__student', 'application__student__user'
        )
        
        # Payment status summary
        payment_summary = disbursements.aggregate(
            total_payments=Count('id'),
            pending_payments=Count('id', filter=Q(status='pending')),
            processing_payments=Count('id', filter=Q(status='processing')),
            completed_payments=Count('id', filter=Q(status='disbursed')),
            failed_payments=Count('id', filter=Q(status='failed')),
            total_amount=Coalesce(Sum('amount'), 0),
            completed_amount=Coalesce(Sum('amount', filter=Q(status='disbursed')), 0)
        )
        
        # Detailed payment records
        payment_details = []
        for disbursement in disbursements[:100]:  # Limit for performance
            payment_details.append({
                'disbursement_id': disbursement.disbursement_id,
                'student_name': disbursement.application.student.user.get_full_name(),
                'student_id': disbursement.application.student.student_id,
                'amount': float(disbursement.amount),
                'status': disbursement.status,
                'payment_method': disbursement.disbursement_method,
                'created_date': disbursement.created_at.date().isoformat(),
                'disbursement_date': disbursement.disbursement_date.date().isoformat() if disbursement.disbursement_date else None,
                'transaction_reference': disbursement.transaction_reference
            })
        
        return {
            'report_type': 'payment_status',
            'payment_summary': payment_summary,
            'payment_details': payment_details,
            'total_records': disbursements.count()
        }
    
    def _export_to_excel(self, report_data, report_type):
        """Export report to Excel format"""
        # This would implement Excel export using openpyxl
        # For now, return JSON with indication of Excel format
        return Response({
            'message': 'Excel export functionality would be implemented here',
            'report_data': report_data,
            'format': 'excel'
        })
    
    def _export_to_pdf(self, report_data, report_type):
        """Export report to PDF format"""
        # This would implement PDF export using reportlab
        # For now, return JSON with indication of PDF format
        return Response({
            'message': 'PDF export functionality would be implemented here',
            'report_data': report_data,
            'format': 'pdf'
        })


class FinanceDashboardView(views.APIView):
    """
    Finance dashboard with key metrics and analytics
    """
    permission_classes = [IsFinanceAdminAuthenticated]
    
    def get(self, request):
        """Get finance dashboard data"""
        try:
            # Check cache first
            cache_key = f"finance_dashboard_{getattr(request, 'finance_admin', {}).get('id', 'system')}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                return Response(cached_data, status=status.HTTP_200_OK)
            
            # Generate fresh dashboard data
            dashboard_data = self._generate_dashboard_data(request)
            
            # Cache for 15 minutes
            cache.set(cache_key, dashboard_data, 900)
            
            serializer = FinanceDashboardSerializer(dashboard_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error generating finance dashboard: {str(e)}")
            return Response(
                {'error': 'Dashboard generation failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_dashboard_data(self, request):
        """Generate comprehensive dashboard data"""
        finance_admin = getattr(request, 'finance_admin', None)
        institute_filter = {}
        
        if finance_admin and finance_admin.institute:
            institute_filter = {'student__institute': finance_admin.institute}
        
        # Current month and year
        now = timezone.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Key metrics
        key_metrics = self._get_key_metrics(institute_filter, current_month_start, current_year_start)
        
        # Charts data
        charts = {
            'monthly_disbursements': self._get_monthly_disbursements_chart(institute_filter),
            'status_distribution': self._get_status_distribution_chart(institute_filter),
            'payment_methods': self._get_payment_methods_chart(institute_filter),
            'budget_utilization': self._get_budget_utilization_chart(institute_filter)
        }
        
        # Recent activities
        recent_activities = self._get_recent_activities(institute_filter)
        
        # Alerts and notifications
        alerts = self._get_dashboard_alerts(institute_filter)
        
        return {
            'dashboard_type': 'finance',
            'generated_at': now.isoformat(),
            'institute_filter': finance_admin.institute.name if finance_admin and finance_admin.institute else 'All Institutes',
            'key_metrics': key_metrics,
            'charts': charts,
            'recent_activities': recent_activities,
            'alerts': alerts
        }
    
    def _get_key_metrics(self, institute_filter, current_month_start, current_year_start):
        """Get key financial metrics"""
        # Base querysets
        applications_qs = ScholarshipApplication.objects.filter(**institute_filter)
        disbursements_qs = ScholarshipDisbursement.objects.filter(
            application__in=applications_qs.values('id')
        )
        
        # Applications metrics
        total_applications = applications_qs.count()
        pending_finance = applications_qs.filter(
            internal_notes__icontains='FORWARDED_TO_FINANCE',
            status__in=['institute_approved', 'dept_approved']
        ).exclude(disbursement__isnull=False).count()
        
        # Disbursement metrics
        total_disbursements = disbursements_qs.count()
        successful_disbursements = disbursements_qs.filter(status='disbursed').count()
        failed_disbursements = disbursements_qs.filter(status='failed').count()
        
        # Financial metrics
        total_disbursed_amount = disbursements_qs.filter(
            status='disbursed'
        ).aggregate(total=Coalesce(Sum('amount'), 0))['total']
        
        monthly_disbursed = disbursements_qs.filter(
            status='disbursed',
            disbursement_date__gte=current_month_start
        ).aggregate(total=Coalesce(Sum('amount'), 0))['total']
        
        yearly_disbursed = disbursements_qs.filter(
            status='disbursed',
            disbursement_date__gte=current_year_start
        ).aggregate(total=Coalesce(Sum('amount'), 0))['total']
        
        # Processing efficiency
        processing_rate = 0
        if total_disbursements > 0:
            processing_rate = (successful_disbursements / total_disbursements) * 100
        
        return {
            'total_applications': total_applications,
            'pending_finance_review': pending_finance,
            'total_disbursements': total_disbursements,
            'successful_disbursements': successful_disbursements,
            'failed_disbursements': failed_disbursements,
            'total_disbursed_amount': float(total_disbursed_amount),
            'monthly_disbursed_amount': float(monthly_disbursed),
            'yearly_disbursed_amount': float(yearly_disbursed),
            'processing_success_rate': round(processing_rate, 2),
            'avg_disbursement_amount': float(total_disbursed_amount / successful_disbursements) if successful_disbursements > 0 else 0
        }
    
    def _get_monthly_disbursements_chart(self, institute_filter):
        """Get monthly disbursements chart data"""
        six_months_ago = timezone.now() - timedelta(days=180)
        
        disbursements = ScholarshipDisbursement.objects.filter(
            application__in=ScholarshipApplication.objects.filter(**institute_filter).values('id'),
            created_at__gte=six_months_ago,
            status='disbursed'
        ).annotate(
            month=TruncMonth('disbursement_date')
        ).values('month').annotate(
            count=Count('id'),
            total_amount=Coalesce(Sum('amount'), 0)
        ).order_by('month')
        
        return list(disbursements)
    
    def _get_status_distribution_chart(self, institute_filter):
        """Get disbursement status distribution"""
        status_data = ScholarshipDisbursement.objects.filter(
            application__in=ScholarshipApplication.objects.filter(**institute_filter).values('id')
        ).values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return list(status_data)
    
    def _get_payment_methods_chart(self, institute_filter):
        """Get payment methods distribution"""
        methods_data = ScholarshipDisbursement.objects.filter(
            application__in=ScholarshipApplication.objects.filter(**institute_filter).values('id'),
            status='disbursed'
        ).values('disbursement_method').annotate(
            count=Count('id'),
            total_amount=Coalesce(Sum('amount'), 0)
        ).order_by('-count')
        
        return list(methods_data)
    
    def _get_budget_utilization_chart(self, institute_filter):
        """Get budget utilization data"""
        budget_filter = {}
        if institute_filter and 'student__institute' in institute_filter:
            budget_filter['institute'] = institute_filter['student__institute']
        
        budgets = Budget.objects.filter(
            is_active=True,
            **budget_filter
        ).values('name', 'budget_type').annotate(
            total_amount=Sum('total_amount'),
            utilized_amount=Sum('utilized_amount')
        )
        
        budget_data = []
        for budget in budgets:
            utilization_percent = 0
            if budget['total_amount'] > 0:
                utilization_percent = (budget['utilized_amount'] / budget['total_amount']) * 100
            
            budget_data.append({
                'name': budget['name'],
                'type': budget['budget_type'],
                'total_amount': float(budget['total_amount']),
                'utilized_amount': float(budget['utilized_amount']),
                'utilization_percent': round(utilization_percent, 2)
            })
        
        return budget_data
    
    def _get_recent_activities(self, institute_filter):
        """Get recent finance activities"""
        recent_disbursements = ScholarshipDisbursement.objects.filter(
            application__in=ScholarshipApplication.objects.filter(**institute_filter).values('id')
        ).select_related(
            'application', 'application__student', 'application__student__user'
        ).order_by('-updated_at')[:10]
        
        activities = []
        for disbursement in recent_disbursements:
            activities.append({
                'type': 'disbursement',
                'title': f'Disbursement {disbursement.status}',
                'description': f'{disbursement.application.student.user.get_full_name()} - ₹{disbursement.amount}',
                'timestamp': disbursement.updated_at.isoformat(),
                'status': disbursement.status,
                'amount': float(disbursement.amount)
            })
        
        return activities
    
    def _get_dashboard_alerts(self, institute_filter):
        """Get dashboard alerts and notifications"""
        alerts = {
            'critical': [],
            'warning': [],
            'info': []
        }
        
        # Critical alerts
        failed_disbursements = ScholarshipDisbursement.objects.filter(
            application__in=ScholarshipApplication.objects.filter(**institute_filter).values('id'),
            status='failed'
        ).count()
        
        if failed_disbursements > 0:
            alerts['critical'].append({
                'title': 'Failed Disbursements',
                'message': f'{failed_disbursements} disbursements have failed',
                'action': 'Review and retry failed payments'
            })
        
        # Warning alerts
        pending_count = ScholarshipApplication.objects.filter(
            **institute_filter,
            internal_notes__icontains='FORWARDED_TO_FINANCE',
            status__in=['institute_approved', 'dept_approved']
        ).exclude(disbursement__isnull=False).count()
        
        if pending_count > 20:
            alerts['warning'].append({
                'title': 'High Pending Queue',
                'message': f'{pending_count} applications pending finance processing',
                'action': 'Process pending applications'
            })
        
        # Info alerts
        recent_completions = ScholarshipDisbursement.objects.filter(
            application__in=ScholarshipApplication.objects.filter(**institute_filter).values('id'),
            status='disbursed',
            disbursement_date__date=timezone.now().date()
        ).count()
        
        if recent_completions > 0:
            alerts['info'].append({
                'title': 'Today\'s Completions',
                'message': f'{recent_completions} disbursements completed today',
                'action': 'View completed disbursements'
            })
        
        return alerts


class BulkDisbursementView(views.APIView):
    """
    Bulk disbursement processing for multiple applications
    """
    permission_classes = [IsFinanceAdminAuthenticated, CanProcessPaymentsPermission]
    
    def post(self, request):
        """Process bulk disbursements"""
        try:
            serializer = BulkPaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Invalid input data', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            application_ids = serializer.validated_data['application_ids']
            disbursement_method = serializer.validated_data['disbursement_method']
            bulk_remarks = serializer.validated_data.get('bulk_remarks', '')
            
            results = []
            total_amount = Decimal('0')
            finance_admin = getattr(request, 'finance_admin', None)
            
            with transaction.atomic():
                for app_id in application_ids:
                    try:
                        application = ScholarshipApplication.objects.select_related(
                            'student', 'student__user', 'student__institute'
                        ).get(application_id=app_id)
                        
                        # Check access permissions
                        if finance_admin and finance_admin.institute:
                            if application.student.institute != finance_admin.institute:
                                results.append({
                                    'application_id': app_id,
                                    'status': 'error',
                                    'message': 'Access denied'
                                })
                                continue
                        
                        # Check if already disbursed
                        if hasattr(application, 'disbursement'):
                            results.append({
                                'application_id': app_id,
                                'status': 'skipped',
                                'message': 'Already has disbursement record'
                            })
                            continue
                        
                        # Create disbursement
                        disbursement_result = self._create_disbursement(
                            application, disbursement_method, bulk_remarks, request.user
                        )
                        
                        if disbursement_result['success']:
                            total_amount += disbursement_result['amount']
                            results.append({
                                'application_id': app_id,
                                'status': 'success',
                                'message': 'Disbursement created successfully',
                                'disbursement_id': disbursement_result['disbursement_id'],
                                'amount': float(disbursement_result['amount'])
                            })
                        else:
                            results.append({
                                'application_id': app_id,
                                'status': 'error',
                                'message': disbursement_result.get('error', 'Creation failed')
                            })
                        
                    except ScholarshipApplication.DoesNotExist:
                        results.append({
                            'application_id': app_id,
                            'status': 'error',
                            'message': 'Application not found'
                        })
                    except Exception as e:
                        logger.error(f"Error creating disbursement for {app_id}: {str(e)}")
                        results.append({
                            'application_id': app_id,
                            'status': 'error',
                            'message': f'Creation failed: {str(e)}'
                        })
            
            # Calculate summary
            success_count = len([r for r in results if r['status'] == 'success'])
            error_count = len([r for r in results if r['status'] == 'error'])
            skipped_count = len([r for r in results if r['status'] == 'skipped'])
            
            return Response({
                'message': f'Bulk disbursement processing completed',
                'summary': {
                    'total_processed': len(application_ids),
                    'successful': success_count,
                    'errors': error_count,
                    'skipped': skipped_count,
                    'total_amount': float(total_amount)
                },
                'results': results,
                'processed_at': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in bulk disbursement processing: {str(e)}")
            return Response(
                {'error': 'Bulk disbursement processing failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _create_disbursement(self, application, method, remarks, user):
        """Create disbursement record for an application"""
        try:
            # Generate disbursement ID
            disbursement_id = f"DISB{timezone.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
            
            # Get student bank details
            student = application.student
            bank_account = getattr(student, 'bank_account_number', None)
            bank_ifsc = getattr(student, 'bank_ifsc_code', None)
            
            # Create disbursement record
            disbursement = ScholarshipDisbursement.objects.create(
                application=application,
                disbursement_id=disbursement_id,
                amount=application.amount_approved or application.amount_requested,
                disbursement_method=method,
                status='pending',
                bank_account_number=bank_account,
                bank_ifsc=bank_ifsc,
                remarks=remarks
            )
            
            return {
                'success': True,
                'disbursement_id': disbursement_id,
                'amount': disbursement.amount
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class FinanceStatisticsView(views.APIView):
    """
    Comprehensive finance statistics and analytics
    """
    permission_classes = [IsFinanceAdminAuthenticated]
    
    def get(self, request):
        """Get detailed finance statistics"""
        try:
            finance_admin = getattr(request, 'finance_admin', None)
            institute_filter = {}
            
            if finance_admin and finance_admin.institute:
                institute_filter = {'student__institute': finance_admin.institute}
            
            # Generate statistics
            statistics = self._generate_comprehensive_statistics(institute_filter)
            
            serializer = FinanceStatisticsSerializer(statistics)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error generating finance statistics: {str(e)}")
            return Response(
                {'error': 'Statistics generation failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_comprehensive_statistics(self, institute_filter):
        """Generate comprehensive finance statistics"""
        # Base querysets
        applications_qs = ScholarshipApplication.objects.filter(**institute_filter)
        disbursements_qs = ScholarshipDisbursement.objects.filter(
            application__in=applications_qs.values('id')
        )
        
        # Application statistics
        app_stats = applications_qs.aggregate(
            total_applications=Count('id'),
            approved_applications=Count('id', filter=Q(status__in=['approved', 'disbursed', 'completed'])),
            rejected_applications=Count('id', filter=Q(status='rejected')),
            pending_applications=Count('id', filter=Q(status__in=['submitted', 'under_review'])),
            total_requested_amount=Coalesce(Sum('amount_requested'), 0),
            total_approved_amount=Coalesce(Sum('amount_approved'), 0)
        )
        
        # Disbursement statistics
        disb_stats = disbursements_qs.aggregate(
            total_disbursements=Count('id'),
            successful_disbursements=Count('id', filter=Q(status='disbursed')),
            failed_disbursements=Count('id', filter=Q(status='failed')),
            pending_disbursements=Count('id', filter=Q(status='pending')),
            processing_disbursements=Count('id', filter=Q(status='processing')),
            total_disbursed_amount=Coalesce(Sum('amount', filter=Q(status='disbursed')), 0),
            avg_disbursement_amount=Coalesce(Avg('amount'), 0)
        )
        
        # Calculate rates and percentages
        approval_rate = 0
        if app_stats['total_applications'] > 0:
            approval_rate = (app_stats['approved_applications'] / app_stats['total_applications']) * 100
        
        disbursement_success_rate = 0
        if disb_stats['total_disbursements'] > 0:
            disbursement_success_rate = (disb_stats['successful_disbursements'] / disb_stats['total_disbursements']) * 100
        
        # Financial efficiency metrics
        amount_approval_rate = 0
        if app_stats['total_requested_amount'] > 0:
            amount_approval_rate = (app_stats['total_approved_amount'] / app_stats['total_requested_amount']) * 100
        
        # Time-based statistics
        current_year = timezone.now().year
        current_month = timezone.now().month
        
        monthly_stats = applications_qs.filter(
            submitted_at__year=current_year,
            submitted_at__month=current_month
        ).aggregate(
            monthly_applications=Count('id'),
            monthly_approved_amount=Coalesce(Sum('amount_approved'), 0)
        )
        
        yearly_stats = applications_qs.filter(
            submitted_at__year=current_year
        ).aggregate(
            yearly_applications=Count('id'),
            yearly_approved_amount=Coalesce(Sum('amount_approved'), 0)
        )
        
        return {
            'generated_at': timezone.now().isoformat(),
            'institute_filter': institute_filter,
            'application_statistics': {
                **app_stats,
                'approval_rate': round(approval_rate, 2),
                'rejection_rate': round(
                    (app_stats['rejected_applications'] / app_stats['total_applications'] * 100) 
                    if app_stats['total_applications'] > 0 else 0, 2
                )
            },
            'disbursement_statistics': {
                **disb_stats,
                'success_rate': round(disbursement_success_rate, 2),
                'failure_rate': round(
                    (disb_stats['failed_disbursements'] / disb_stats['total_disbursements'] * 100)
                    if disb_stats['total_disbursements'] > 0 else 0, 2
                )
            },
            'financial_metrics': {
                'amount_approval_rate': round(amount_approval_rate, 2),
                'avg_requested_amount': float(
                    app_stats['total_requested_amount'] / app_stats['total_applications']
                    if app_stats['total_applications'] > 0 else 0
                ),
                'avg_approved_amount': float(
                    app_stats['total_approved_amount'] / app_stats['approved_applications']
                    if app_stats['approved_applications'] > 0 else 0
                )
            },
            'time_based_statistics': {
                'current_month': monthly_stats,
                'current_year': yearly_stats
            }
        }
