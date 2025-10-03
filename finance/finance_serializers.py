"""
Finance Module Serializers
Comprehensive serializers for finance operations
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from decimal import Decimal
import json

from .models import (
    ScholarshipScheme, ScholarshipDisbursement, FinanceAdmin, 
    Budget, Transaction, FinancialReport
)
from students.models import Student, ScholarshipApplication
from institutes.models import Institute
from authentication.models import CustomUser

User = get_user_model()


class FinanceApplicationListSerializer(serializers.ModelSerializer):
    """Serializer for applications pending finance processing"""
    
    student_details = serializers.SerializerMethodField()
    institute_name = serializers.CharField(source='student.institute.name', read_only=True)
    department_name = serializers.CharField(source='student.department.name', read_only=True)
    days_in_finance_queue = serializers.SerializerMethodField()
    processing_priority = serializers.SerializerMethodField()
    has_bank_details = serializers.SerializerMethodField()
    eligibility_verified = serializers.SerializerMethodField()
    
    class Meta:
        model = ScholarshipApplication
        fields = [
            'id', 'application_id', 'student_details', 'institute_name', 'department_name',
            'scholarship_type', 'scholarship_name', 'amount_requested', 'amount_approved',
            'status', 'priority', 'reason', 'submitted_at', 'approved_at',
            'days_in_finance_queue', 'processing_priority', 'has_bank_details',
            'eligibility_verified', 'eligibility_score', 'document_completeness_score'
        ]
    
    def get_student_details(self, obj):
        student = obj.student
        return {
            'student_id': student.student_id,
            'name': student.user.get_full_name(),
            'email': student.user.email,
            'phone': student.user.phone_number,
            'course_level': student.course_level,
            'course_name': student.course_name,
            'academic_year': student.academic_year,
            'cgpa': float(student.cgpa) if student.cgpa else None
        }
    
    def get_days_in_finance_queue(self, obj):
        """Calculate days since forwarded to finance"""
        if 'FORWARDED_TO_FINANCE' in (obj.internal_notes or ''):
            # Try to extract forward date from internal notes
            # In real implementation, this would be tracked separately
            return (timezone.now() - obj.approved_at).days if obj.approved_at else 0
        return 0
    
    def get_processing_priority(self, obj):
        """Calculate processing priority based on various factors"""
        priority_score = 0
        
        # Base priority from application
        priority_map = {'urgent': 4, 'high': 3, 'medium': 2, 'low': 1}
        priority_score += priority_map.get(obj.priority, 2)
        
        # Amount factor
        if obj.amount_approved:
            if obj.amount_approved > 75000:
                priority_score += 2
            elif obj.amount_approved > 50000:
                priority_score += 1
        
        # Days in queue factor
        days_in_queue = self.get_days_in_finance_queue(obj)
        if days_in_queue > 7:
            priority_score += 2
        elif days_in_queue > 3:
            priority_score += 1
        
        # Return priority level
        if priority_score >= 6:
            return 'urgent'
        elif priority_score >= 4:
            return 'high'
        elif priority_score >= 2:
            return 'medium'
        else:
            return 'low'
    
    def get_has_bank_details(self, obj):
        """Check if student has complete bank details"""
        student = obj.student
        return bool(
            getattr(student, 'bank_account_number', None) and
            getattr(student, 'bank_ifsc_code', None) and
            getattr(student, 'bank_name', None)
        )
    
    def get_eligibility_verified(self, obj):
        """Check if eligibility is verified"""
        return obj.eligibility_score >= 70 and obj.document_completeness_score >= 80


class ScholarshipCalculationSerializer(serializers.Serializer):
    """Serializer for scholarship amount calculation requests"""
    
    CALCULATION_TYPES = [
        ('standard', 'Standard Calculation'),
        ('need_based', 'Need-based Calculation'),
        ('merit_based', 'Merit-based Calculation'),
        ('government_scheme', 'Government Scheme'),
        ('custom', 'Custom Calculation')
    ]
    
    application_id = serializers.CharField(max_length=30, required=True)
    calculation_type = serializers.ChoiceField(choices=CALCULATION_TYPES, default='standard')
    custom_factors = serializers.DictField(required=False, default=dict)
    
    def validate_application_id(self, value):
        """Validate application exists and is eligible for calculation"""
        try:
            application = ScholarshipApplication.objects.get(application_id=value)
            if not application.amount_approved and not application.amount_requested:
                raise serializers.ValidationError("Application has no amount to calculate")
            return value
        except ScholarshipApplication.DoesNotExist:
            raise serializers.ValidationError("Application not found")
    
    def validate_custom_factors(self, value):
        """Validate custom calculation factors"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Custom factors must be a dictionary")
        
        # Validate specific fields if present
        valid_keys = [
            'family_income', 'state_category', 'rural_urban', 'multipliers', 'adjustments'
        ]
        
        for key in value.keys():
            if key not in valid_keys:
                raise serializers.ValidationError(f"Invalid custom factor: {key}")
        
        return value


class PaymentStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating payment status"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('disbursed', 'Disbursed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed')
    ]
    
    COMPONENT_TYPES = [
        ('tuition', 'Tuition Fee'),
        ('maintenance', 'Maintenance Allowance'),
        ('books', 'Books and Materials'),
        ('other', 'Other')
    ]
    
    disbursement_ids = serializers.ListField(
        child=serializers.CharField(max_length=30),
        min_length=1,
        max_length=50,
        help_text="List of disbursement IDs to update"
    )
    payment_status = serializers.ChoiceField(choices=STATUS_CHOICES, required=True)
    payment_components = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="List of payment components with details"
    )
    payment_remarks = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    def validate_disbursement_ids(self, value):
        """Validate disbursement IDs exist"""
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Duplicate disbursement IDs found")
        
        # Check if all disbursements exist
        existing_count = ScholarshipDisbursement.objects.filter(
            disbursement_id__in=value
        ).count()
        
        if existing_count != len(value):
            raise serializers.ValidationError("One or more disbursement IDs not found")
        
        return value
    
    def validate_payment_components(self, value):
        """Validate payment components structure"""
        if value:
            for component in value:
                required_fields = ['type', 'amount', 'is_paid']
                for field in required_fields:
                    if field not in component:
                        raise serializers.ValidationError(f"Component missing required field: {field}")
                
                if component['type'] not in [choice[0] for choice in self.COMPONENT_TYPES]:
                    raise serializers.ValidationError(f"Invalid component type: {component['type']}")
                
                if not isinstance(component['amount'], (int, float)) or component['amount'] < 0:
                    raise serializers.ValidationError("Component amount must be a positive number")
        
        return value


class DBTTransferSerializer(serializers.Serializer):
    """Serializer for DBT transfer simulation"""
    
    disbursement_ids = serializers.ListField(
        child=serializers.CharField(max_length=30),
        min_length=1,
        max_length=100,
        help_text="List of disbursement IDs for DBT transfer"
    )
    transfer_remarks = serializers.CharField(
        max_length=500, 
        required=False, 
        allow_blank=True,
        help_text="Remarks for the transfer batch"
    )
    
    def validate_disbursement_ids(self, value):
        """Validate disbursement IDs for DBT transfer"""
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Duplicate disbursement IDs found")
        
        # Check if disbursements exist and are ready for transfer
        disbursements = ScholarshipDisbursement.objects.filter(
            disbursement_id__in=value,
            status__in=['pending', 'processing']
        )
        
        if disbursements.count() != len(value):
            invalid_ids = set(value) - set(disbursements.values_list('disbursement_id', flat=True))
            raise serializers.ValidationError(
                f"Invalid or already processed disbursements: {list(invalid_ids)}"
            )
        
        # Check bank details completeness
        incomplete_bank_details = []
        for disbursement in disbursements:
            if not disbursement.bank_account_number or not disbursement.bank_ifsc:
                incomplete_bank_details.append(disbursement.disbursement_id)
        
        if incomplete_bank_details:
            raise serializers.ValidationError(
                f"Incomplete bank details for disbursements: {incomplete_bank_details}"
            )
        
        return value


class BulkPaymentSerializer(serializers.Serializer):
    """Serializer for bulk payment processing"""
    
    DISBURSEMENT_METHODS = [
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('cash', 'Cash'),
        ('fee_adjustment', 'Fee Adjustment')
    ]
    
    application_ids = serializers.ListField(
        child=serializers.CharField(max_length=30),
        min_length=1,
        max_length=100,
        help_text="List of application IDs for bulk disbursement"
    )
    disbursement_method = serializers.ChoiceField(choices=DISBURSEMENT_METHODS, required=True)
    bulk_remarks = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    def validate_application_ids(self, value):
        """Validate application IDs for bulk processing"""
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Duplicate application IDs found")
        
        # Check if applications exist and are ready for disbursement
        applications = ScholarshipApplication.objects.filter(
            application_id__in=value,
            status__in=['institute_approved', 'dept_approved'],
            internal_notes__icontains='FORWARDED_TO_FINANCE'
        ).exclude(disbursement__isnull=False)
        
        if applications.count() != len(value):
            invalid_ids = set(value) - set(applications.values_list('application_id', flat=True))
            raise serializers.ValidationError(
                f"Invalid or already processed applications: {list(invalid_ids)}"
            )
        
        return value


class ScholarshipDisbursementSerializer(serializers.ModelSerializer):
    """Comprehensive disbursement serializer"""
    
    application_details = serializers.SerializerMethodField()
    student_details = serializers.SerializerMethodField()
    payment_breakdown = serializers.SerializerMethodField()
    processing_history = serializers.SerializerMethodField()
    
    class Meta:
        model = ScholarshipDisbursement
        fields = [
            'id', 'disbursement_id', 'application_details', 'student_details',
            'amount', 'disbursement_method', 'status', 'bank_account_number',
            'bank_ifsc', 'cheque_number', 'transaction_reference',
            'disbursed_by', 'disbursement_date', 'remarks', 'payment_breakdown',
            'processing_history', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_application_details(self, obj):
        application = obj.application
        return {
            'application_id': application.application_id,
            'scholarship_type': application.scholarship_type,
            'scholarship_name': application.scholarship_name,
            'amount_requested': float(application.amount_requested),
            'amount_approved': float(application.amount_approved) if application.amount_approved else None,
            'status': application.status,
            'priority': application.priority
        }
    
    def get_student_details(self, obj):
        student = obj.application.student
        return {
            'student_id': student.student_id,
            'name': student.user.get_full_name(),
            'email': student.user.email,
            'phone': student.user.phone_number,
            'institute': student.institute.name,
            'department': student.department.name if student.department else None,
            'course_level': student.course_level,
            'course_name': student.course_name
        }
    
    def get_payment_breakdown(self, obj):
        """Calculate payment breakdown"""
        total_amount = float(obj.amount)
        
        # Standard breakdown (can be customized)
        return {
            'total_amount': total_amount,
            'tuition_fee': round(total_amount * 0.7, 2),
            'maintenance_allowance': round(total_amount * 0.25, 2),
            'books_and_materials': round(total_amount * 0.05, 2)
        }
    
    def get_processing_history(self, obj):
        """Get processing history from related transactions"""
        transactions = Transaction.objects.filter(
            disbursement=obj
        ).order_by('created_at')
        
        history = []
        for txn in transactions:
            history.append({
                'transaction_id': txn.transaction_id,
                'type': txn.transaction_type,
                'amount': float(txn.amount),
                'description': txn.description,
                'processed_by': txn.processed_by.get_full_name() if txn.processed_by else None,
                'transaction_date': txn.transaction_date.isoformat()
            })
        
        return history


class DisbursementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating disbursements"""
    
    class Meta:
        model = ScholarshipDisbursement
        fields = [
            'application', 'amount', 'disbursement_method', 
            'bank_account_number', 'bank_ifsc', 'cheque_number', 'remarks'
        ]
    
    def validate_application(self, value):
        """Validate application is eligible for disbursement"""
        if hasattr(value, 'disbursement'):
            raise serializers.ValidationError("Application already has a disbursement record")
        
        if value.status not in ['institute_approved', 'dept_approved']:
            raise serializers.ValidationError("Application not approved for disbursement")
        
        if 'FORWARDED_TO_FINANCE' not in (value.internal_notes or ''):
            raise serializers.ValidationError("Application not forwarded to finance")
        
        return value
    
    def validate_amount(self, value):
        """Validate disbursement amount"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        
        if value > 500000:  # Max limit
            raise serializers.ValidationError("Amount exceeds maximum limit")
        
        return value


class TransactionSerializer(serializers.ModelSerializer):
    """Transaction serializer"""
    
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    institute_name = serializers.CharField(source='institute.name', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_id', 'institute_name', 'transaction_type',
            'category', 'amount', 'description', 'reference_number',
            'student_name', 'processed_by_name', 'transaction_date',
            'created_at'
        ]


class BudgetSerializer(serializers.ModelSerializer):
    """Budget serializer with utilization details"""
    
    institute_name = serializers.CharField(source='institute.name', read_only=True)
    utilization_percentage = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    
    class Meta:
        model = Budget
        fields = [
            'id', 'name', 'budget_type', 'institute_name', 'total_amount',
            'allocated_amount', 'utilized_amount', 'remaining_amount',
            'utilization_percentage', 'financial_year', 'description',
            'created_by_name', 'approved_by_name', 'approval_date',
            'is_active', 'created_at', 'updated_at'
        ]
    
    def get_utilization_percentage(self, obj):
        """Calculate utilization percentage"""
        if obj.total_amount > 0:
            return round((obj.utilized_amount / obj.total_amount) * 100, 2)
        return 0
    
    def get_remaining_amount(self, obj):
        """Calculate remaining amount"""
        return float(obj.total_amount - obj.utilized_amount)


class ScholarshipSchemeSerializer(serializers.ModelSerializer):
    """Scholarship scheme serializer"""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    remaining_budget = serializers.SerializerMethodField()
    budget_utilization_percentage = serializers.SerializerMethodField()
    is_currently_active = serializers.SerializerMethodField()
    
    class Meta:
        model = ScholarshipScheme
        fields = [
            'id', 'name', 'code', 'description', 'scheme_type', 'eligibility_type',
            'min_amount', 'max_amount', 'total_budget', 'utilized_budget',
            'remaining_budget', 'budget_utilization_percentage', 'min_cgpa',
            'min_percentage', 'max_family_income', 'application_start_date',
            'application_end_date', 'academic_year', 'status', 'renewable',
            'max_duration_years', 'is_currently_active', 'created_by_name',
            'created_at', 'updated_at'
        ]
    
    def get_remaining_budget(self, obj):
        return float(obj.total_budget - obj.utilized_budget)
    
    def get_budget_utilization_percentage(self, obj):
        if obj.total_budget > 0:
            return round((obj.utilized_budget / obj.total_budget) * 100, 2)
        return 0
    
    def get_is_currently_active(self, obj):
        return obj.is_active


class FinanceReportSerializer(serializers.Serializer):
    """Serializer for finance reports"""
    
    report_type = serializers.CharField()
    report_metadata = serializers.DictField()
    
    # Summary fields (conditional based on report type)
    summary = serializers.DictField(required=False)
    overall_summary = serializers.DictField(required=False)
    
    # Breakdown fields
    status_breakdown = serializers.ListField(child=serializers.DictField(), required=False)
    method_breakdown = serializers.ListField(child=serializers.DictField(), required=False)
    category_breakdown = serializers.ListField(child=serializers.DictField(), required=False)
    
    # Trend data
    monthly_trend = serializers.ListField(child=serializers.DictField(), required=False)
    daily_trend = serializers.ListField(child=serializers.DictField(), required=False)
    
    # Detailed data
    budget_details = serializers.ListField(child=serializers.DictField(), required=False)
    payment_details = serializers.ListField(child=serializers.DictField(), required=False)
    
    # Analysis data
    type_wise_analysis = serializers.ListField(child=serializers.DictField(), required=False)
    status_distribution = serializers.ListField(child=serializers.DictField(), required=False)
    department_wise_analysis = serializers.ListField(child=serializers.DictField(), required=False)
    institute_breakdown = serializers.ListField(child=serializers.DictField(), required=False)
    
    # Summary statistics
    application_summary = serializers.DictField(required=False)
    disbursement_summary = serializers.DictField(required=False)
    financial_efficiency = serializers.DictField(required=False)
    payment_summary = serializers.DictField(required=False)
    
    # Additional fields
    period = serializers.CharField(required=False)
    total_records = serializers.IntegerField(required=False)


class FinanceDashboardSerializer(serializers.Serializer):
    """Serializer for finance dashboard data"""
    
    dashboard_type = serializers.CharField()
    generated_at = serializers.DateTimeField()
    institute_filter = serializers.CharField()
    
    # Key metrics
    key_metrics = serializers.DictField()
    
    # Charts data
    charts = serializers.DictField()
    
    # Recent activities
    recent_activities = serializers.ListField(child=serializers.DictField())
    
    # Alerts and notifications
    alerts = serializers.DictField()


class FinanceStatisticsSerializer(serializers.Serializer):
    """Serializer for comprehensive finance statistics"""
    
    generated_at = serializers.DateTimeField()
    institute_filter = serializers.DictField()
    
    # Application statistics
    application_statistics = serializers.DictField()
    
    # Disbursement statistics
    disbursement_statistics = serializers.DictField()
    
    # Financial metrics
    financial_metrics = serializers.DictField()
    
    # Time-based statistics
    time_based_statistics = serializers.DictField()


class DisbursementReportSerializer(serializers.Serializer):
    """Serializer for disbursement reports"""
    
    disbursement_id = serializers.CharField()
    student_name = serializers.CharField()
    student_id = serializers.CharField()
    institute = serializers.CharField()
    department = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField()
    disbursement_method = serializers.CharField()
    disbursement_date = serializers.DateTimeField(allow_null=True)
    transaction_reference = serializers.CharField(allow_null=True)
    remarks = serializers.CharField(allow_null=True)


class FinanceAdminSerializer(serializers.ModelSerializer):
    """Finance admin serializer"""
    
    user_details = serializers.SerializerMethodField()
    institute_name = serializers.CharField(source='institute.name', read_only=True)
    
    class Meta:
        model = FinanceAdmin
        fields = [
            'id', 'user', 'user_details', 'employee_id', 'institute',
            'institute_name', 'designation', 'permissions', 'is_primary_admin',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_user_details(self, obj):
        return {
            'id': obj.user.id,
            'email': obj.user.email,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'full_name': obj.user.get_full_name(),
            'phone_number': obj.user.phone_number,
            'is_active': obj.user.is_active
        }


class FinanceChoicesSerializer(serializers.Serializer):
    """Serializer for finance-related choices"""
    
    disbursement_methods = serializers.ListField(child=serializers.DictField(), read_only=True)
    disbursement_statuses = serializers.ListField(child=serializers.DictField(), read_only=True)
    transaction_types = serializers.ListField(child=serializers.DictField(), read_only=True)
    transaction_categories = serializers.ListField(child=serializers.DictField(), read_only=True)
    budget_types = serializers.ListField(child=serializers.DictField(), read_only=True)
    scheme_types = serializers.ListField(child=serializers.DictField(), read_only=True)
    
    def to_representation(self, instance):
        return {
            'disbursement_methods': [
                {'value': choice[0], 'label': choice[1]}
                for choice in ScholarshipDisbursement.DISBURSEMENT_METHOD
            ],
            'disbursement_statuses': [
                {'value': choice[0], 'label': choice[1]}
                for choice in ScholarshipDisbursement.DISBURSEMENT_STATUS
            ],
            'transaction_types': [
                {'value': choice[0], 'label': choice[1]}
                for choice in Transaction.TRANSACTION_TYPES
            ],
            'transaction_categories': [
                {'value': choice[0], 'label': choice[1]}
                for choice in Transaction.TRANSACTION_CATEGORIES
            ],
            'budget_types': [
                {'value': choice[0], 'label': choice[1]}
                for choice in Budget.BUDGET_TYPES
            ],
            'scheme_types': [
                {'value': choice[0], 'label': choice[1]}
                for choice in ScholarshipScheme.SCHEME_TYPES
            ]
        }


# Response Serializers
class CalculationResponseSerializer(serializers.Serializer):
    """Response serializer for scholarship calculation"""
    
    application_id = serializers.CharField()
    student_name = serializers.CharField()
    calculation_type = serializers.CharField()
    calculation_factors = serializers.DictField()
    calculated_amounts = serializers.DictField()
    breakdown = serializers.DictField()
    recommendations = serializers.ListField(child=serializers.DictField())
    calculated_at = serializers.DateTimeField()


class PaymentUpdateResponseSerializer(serializers.Serializer):
    """Response serializer for payment status updates"""
    
    message = serializers.CharField()
    summary = serializers.DictField()
    results = serializers.ListField(child=serializers.DictField())


class DBTTransferResponseSerializer(serializers.Serializer):
    """Response serializer for DBT transfers"""
    
    transfer_batch_id = serializers.CharField()
    message = serializers.CharField()
    summary = serializers.DictField()
    results = serializers.ListField(child=serializers.DictField())
    processed_at = serializers.DateTimeField()


class BulkDisbursementResponseSerializer(serializers.Serializer):
    """Response serializer for bulk disbursements"""
    
    message = serializers.CharField()
    summary = serializers.DictField()
    results = serializers.ListField(child=serializers.DictField())
    processed_at = serializers.DateTimeField()
