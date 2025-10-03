"""
Institute Module Serializers
Comprehensive serializers for Institute administration and application management
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Avg
from django.utils import timezone

from .models import Institute, InstituteAdmin, InstituteBankAccount, InstituteDocument
from students.models import Student, ScholarshipApplication, StudentDocument, DocumentVerification
from departments.models import Department
from authentication.models import CustomUser

User = get_user_model()


class InstituteBasicSerializer(serializers.ModelSerializer):
    """Basic institute information serializer"""
    
    class Meta:
        model = Institute
        fields = [
            'id', 'name', 'code', 'institute_type', 'city', 'state',
            'established_year', 'website', 'is_active'
        ]


class InstituteSerializer(serializers.ModelSerializer):
    """Complete institute serializer with all details"""
    
    total_students = serializers.SerializerMethodField()
    total_applications = serializers.SerializerMethodField()
    admin_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Institute
        fields = [
            'id', 'name', 'code', 'institute_type', 'established_year',
            'address', 'city', 'state', 'country', 'postal_code',
            'phone_number', 'email', 'website', 'accreditation',
            'accreditation_grade', 'principal_name', 'principal_email',
            'principal_phone', 'is_active', 'created_at', 'updated_at',
            'total_students', 'total_applications', 'admin_count'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_students(self, obj):
        return obj.students.filter(is_active=True).count()
    
    def get_total_applications(self, obj):
        return ScholarshipApplication.objects.filter(student__institute=obj).count()
    
    def get_admin_count(self, obj):
        return obj.admins.count()


class InstituteDetailSerializer(InstituteSerializer):
    """Detailed institute serializer with related data"""
    
    departments = serializers.SerializerMethodField()
    recent_applications = serializers.SerializerMethodField()
    bank_accounts = serializers.SerializerMethodField()
    
    class Meta(InstituteSerializer.Meta):
        fields = InstituteSerializer.Meta.fields + [
            'departments', 'recent_applications', 'bank_accounts'
        ]
    
    def get_departments(self, obj):
        departments = Department.objects.filter(institute=obj, is_active=True)
        return [{'id': dept.id, 'name': dept.name, 'code': dept.code} for dept in departments]
    
    def get_recent_applications(self, obj):
        recent_apps = ScholarshipApplication.objects.filter(
            student__institute=obj
        ).select_related('student', 'student__user').order_by('-submitted_at')[:5]
        
        return [{
            'application_id': app.application_id,
            'student_name': app.student.user.get_full_name(),
            'scholarship_type': app.scholarship_type,
            'amount_requested': app.amount_requested,
            'status': app.status,
            'submitted_at': app.submitted_at
        } for app in recent_apps]
    
    def get_bank_accounts(self, obj):
        accounts = obj.bank_accounts.filter(is_active=True)
        return [{
            'id': acc.id,
            'account_name': acc.account_name,
            'account_number': acc.account_number[-4:] if acc.account_number else '',  # Mask account number
            'bank_name': acc.bank_name,
            'is_primary': acc.is_primary
        } for acc in accounts]


class InstituteAdminSerializer(serializers.ModelSerializer):
    """Institute admin serializer"""
    
    user_details = serializers.SerializerMethodField()
    institute_name = serializers.CharField(source='institute.name', read_only=True)
    
    class Meta:
        model = InstituteAdmin
        fields = [
            'id', 'user', 'user_details', 'institute', 'institute_name',
            'designation', 'employee_id', 'is_primary_admin',
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


class StudentBasicSerializer(serializers.ModelSerializer):
    """Basic student information for lists"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    
    class Meta:
        model = Student
        fields = [
            'id', 'student_id', 'user_name', 'user_email',
            'department_name', 'course_level', 'course_name',
            'academic_year', 'cgpa', 'is_active', 'is_verified'
        ]


class DocumentVerificationStatusSerializer(serializers.ModelSerializer):
    """Document verification status serializer"""
    
    document_name = serializers.CharField(source='document.document_name', read_only=True)
    document_type = serializers.CharField(source='document.document_type', read_only=True)
    
    class Meta:
        model = DocumentVerification
        fields = [
            'id', 'document_name', 'document_type', 'status',
            'verification_level', 'compliance_score', 'verification_date',
            'rejection_reason', 'verification_notes'
        ]


class StudentApplicationListSerializer(serializers.ModelSerializer):
    """Serializer for listing student scholarship applications in institute view"""
    
    student_details = StudentBasicSerializer(source='student', read_only=True)
    documents_status = serializers.SerializerMethodField()
    processing_time_days = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    
    class Meta:
        model = ScholarshipApplication
        fields = [
            'id', 'application_id', 'student_details', 'scholarship_type',
            'scholarship_name', 'amount_requested', 'amount_approved',
            'status', 'priority', 'reason', 'submitted_at', 'review_started_at',
            'review_completed_at', 'processing_time_days', 'is_overdue',
            'eligibility_score', 'document_completeness_score',
            'assigned_to_name', 'reviewed_by_name', 'documents_status',
            'academic_year', 'auto_eligible', 'manual_review_required'
        ]
    
    def get_documents_status(self, obj):
        """Get document verification status summary"""
        student_docs = obj.student.documents.all()
        return {
            'total_documents': student_docs.count(),
            'verified_documents': student_docs.filter(is_verified=True).count(),
            'pending_documents': student_docs.filter(is_verified=False, status='uploaded').count(),
            'rejected_documents': student_docs.filter(status='rejected').count(),
            'completeness_percentage': obj.document_completeness_score
        }
    
    def get_processing_time_days(self, obj):
        """Calculate processing time in days"""
        if obj.submitted_at:
            if obj.review_completed_at:
                return (obj.review_completed_at - obj.submitted_at).days
            else:
                return (timezone.now() - obj.submitted_at).days
        return 0
    
    def get_is_overdue(self, obj):
        """Check if application is overdue (>30 days)"""
        return obj.is_overdue


class ApplicationApprovalSerializer(serializers.Serializer):
    """Serializer for application approval/rejection actions"""
    
    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('request_documents', 'Request Additional Documents'),
        ('hold', 'Put on Hold'),
    ]
    
    action = serializers.ChoiceField(choices=ACTION_CHOICES, required=True)
    remarks = serializers.CharField(max_length=1000, required=True, help_text="Reason for the action")
    internal_notes = serializers.CharField(max_length=2000, required=False, allow_blank=True, help_text="Internal notes for team reference")
    approved_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True, help_text="Approved amount (for approve action)")
    
    def validate(self, data):
        action = data.get('action')
        approved_amount = data.get('approved_amount')
        
        # If approving, we can optionally specify an amount
        if action == 'approve' and approved_amount is not None:
            if approved_amount <= 0:
                raise serializers.ValidationError("Approved amount must be greater than 0")
        
        return data


class BulkApplicationActionSerializer(serializers.Serializer):
    """Serializer for bulk application actions"""
    
    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('assign', 'Assign Reviewer'),
    ]
    
    application_ids = serializers.ListField(
        child=serializers.CharField(max_length=30),
        min_length=1,
        max_length=50,
        help_text="List of application IDs to process"
    )
    action = serializers.ChoiceField(choices=ACTION_CHOICES, required=True)
    remarks = serializers.CharField(max_length=1000, required=True, help_text="Reason for the bulk action")
    assigned_to = serializers.IntegerField(required=False, help_text="User ID to assign applications to (for assign action)")
    
    def validate(self, data):
        action = data.get('action')
        assigned_to = data.get('assigned_to')
        
        if action == 'assign' and not assigned_to:
            raise serializers.ValidationError("assigned_to is required for assign action")
        
        return data


class ApplicationStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for application status updates response"""
    
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    
    class Meta:
        model = ScholarshipApplication
        fields = [
            'id', 'application_id', 'student_name', 'scholarship_type',
            'amount_requested', 'amount_approved', 'status', 'priority',
            'review_comments', 'rejection_reason', 'approved_at',
            'rejected_at', 'updated_at'
        ]


class ApplicationTrackingSerializer(serializers.Serializer):
    """Serializer for detailed application tracking information"""
    
    application = StudentApplicationListSerializer(read_only=True)
    timeline = serializers.ListField(child=serializers.DictField(), read_only=True)
    document_status = serializers.DictField(read_only=True)
    processing_stats = serializers.DictField(read_only=True)
    next_steps = serializers.ListField(child=serializers.CharField(), read_only=True)
    workflow_history = serializers.ListField(child=serializers.DictField(), read_only=True)


class ApplicationCommentsSerializer(serializers.Serializer):
    """Serializer for application comments"""
    
    comment = serializers.CharField(max_length=2000, required=True, help_text="Comment text")
    is_internal = serializers.BooleanField(default=False, help_text="Whether this is an internal comment")


class ApplicationReportSerializer(serializers.Serializer):
    """Serializer for application reports"""
    
    application_id = serializers.CharField()
    student_id = serializers.CharField()
    student_name = serializers.CharField()
    department = serializers.CharField()
    course_level = serializers.CharField()
    scholarship_type = serializers.CharField()
    scholarship_name = serializers.CharField()
    amount_requested = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_approved = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    status = serializers.CharField()
    priority = serializers.CharField()
    submitted_at = serializers.DateTimeField()
    review_completed_at = serializers.DateTimeField(allow_null=True)
    processing_time = serializers.IntegerField(allow_null=True)
    eligibility_score = serializers.IntegerField()
    document_completeness_score = serializers.IntegerField()


class InstituteReportSerializer(serializers.Serializer):
    """Serializer for institute reports"""
    
    report_type = serializers.CharField()
    institute = serializers.CharField()
    generated_at = serializers.DateTimeField()
    
    # Summary report fields
    total_applications = serializers.IntegerField(required=False)
    total_requested_amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    total_approved_amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    approval_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    average_processing_time = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    status_breakdown = serializers.ListField(child=serializers.DictField(), required=False)
    type_breakdown = serializers.ListField(child=serializers.DictField(), required=False)
    monthly_trends = serializers.ListField(child=serializers.DictField(), required=False)
    
    # Detailed report fields
    total_records = serializers.IntegerField(required=False)
    applications = serializers.ListField(child=ApplicationReportSerializer(), required=False)
    
    # Financial report fields
    financial_summary = serializers.DictField(required=False)
    amount_range_analysis = serializers.ListField(child=serializers.DictField(), required=False)
    top_scholarship_types = serializers.ListField(child=serializers.DictField(), required=False)
    
    # Monthly report fields
    monthly_data = serializers.ListField(child=serializers.DictField(), required=False)
    
    # Department-wise report fields
    department_analysis = serializers.ListField(child=serializers.DictField(), required=False)
    
    # Trend analysis fields
    weekly_trends = serializers.ListField(child=serializers.DictField(), required=False)
    growth_metrics = serializers.DictField(required=False)


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer for document uploads with validation"""
    
    class Meta:
        model = StudentDocument
        fields = [
            'id', 'document_type', 'document_name', 'document_file',
            'document_number', 'issue_date', 'expiry_date',
            'issuing_authority', 'description', 'is_mandatory'
        ]
    
    def validate_document_file(self, value):
        """Validate uploaded document file"""
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 10MB")
        
        # Check file format
        allowed_formats = ['pdf', 'jpg', 'jpeg', 'png']
        file_extension = value.name.split('.')[-1].lower()
        if file_extension not in allowed_formats:
            raise serializers.ValidationError(f"File format not allowed. Allowed formats: {', '.join(allowed_formats)}")
        
        return value


class DocumentVerificationSerializer(serializers.ModelSerializer):
    """Serializer for document verification by institute admin"""
    
    document_details = serializers.SerializerMethodField()
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    
    class Meta:
        model = DocumentVerification
        fields = [
            'id', 'document_details', 'status', 'verification_level',
            'verification_date', 'rejection_reason', 'verification_notes',
            'verification_checklist', 'compliance_score', 'verified_by_name',
            'auto_verified', 'manual_review_required', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'verified_by_name']
    
    def get_document_details(self, obj):
        """Get basic document details"""
        return {
            'id': obj.document.id,
            'document_type': obj.document.document_type,
            'document_name': obj.document.document_name,
            'file_size_mb': obj.document.file_size_mb,
            'uploaded_at': obj.document.uploaded_at,
            'is_mandatory': obj.document.is_mandatory
        }


class InstituteBankAccountSerializer(serializers.ModelSerializer):
    """Serializer for institute bank accounts"""
    
    class Meta:
        model = InstituteBankAccount
        fields = [
            'id', 'account_name', 'account_number', 'bank_name',
            'branch_name', 'ifsc_code', 'account_type', 'is_primary',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def to_representation(self, instance):
        """Mask account number for security"""
        data = super().to_representation(instance)
        if instance.account_number:
            # Show only last 4 digits
            masked_number = '*' * (len(instance.account_number) - 4) + instance.account_number[-4:]
            data['account_number'] = masked_number
        return data


class InstituteDocumentSerializer(serializers.ModelSerializer):
    """Serializer for institute documents"""
    
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = InstituteDocument
        fields = [
            'id', 'document_type', 'document_name', 'document_file',
            'description', 'expiry_date', 'is_verified', 'verified_by_name',
            'verification_date', 'file_size_mb', 'is_expired', 'uploaded_at'
        ]
        read_only_fields = ['uploaded_at', 'verified_by_name', 'verification_date']
    
    def get_file_size_mb(self, obj):
        """Get file size in MB"""
        if obj.document_file and hasattr(obj.document_file.file, 'size'):
            return round(obj.document_file.file.size / (1024 * 1024), 2)
        return 0
    
    def get_is_expired(self, obj):
        """Check if document has expired"""
        if obj.expiry_date:
            return obj.expiry_date < timezone.now().date()
        return False


class StudentVerificationSerializer(serializers.ModelSerializer):
    """Serializer for student verification by institute"""
    
    user_details = serializers.SerializerMethodField()
    department_details = serializers.SerializerMethodField()
    documents_summary = serializers.SerializerMethodField()
    academic_records = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = [
            'id', 'student_id', 'user_details', 'department_details',
            'course_level', 'course_name', 'academic_year', 'enrollment_date',
            'cgpa', 'roll_number', 'admission_type', 'category',
            'father_name', 'mother_name', 'family_income', 'is_verified',
            'verification_date', 'documents_summary', 'academic_records'
        ]
        read_only_fields = ['student_id', 'verification_date']
    
    def get_user_details(self, obj):
        """Get user account details"""
        return {
            'email': obj.user.email,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'phone_number': obj.user.phone_number,
            'date_of_birth': obj.user.date_of_birth,
            'gender': obj.user.gender,
            'address': obj.user.address
        }
    
    def get_department_details(self, obj):
        """Get department information"""
        return {
            'id': obj.department.id,
            'name': obj.department.name,
            'code': obj.department.code
        }
    
    def get_documents_summary(self, obj):
        """Get documents verification summary"""
        docs = obj.documents.all()
        return {
            'total_documents': docs.count(),
            'verified_documents': docs.filter(is_verified=True).count(),
            'pending_documents': docs.filter(is_verified=False).count(),
            'rejected_documents': docs.filter(status='rejected').count(),
            'mandatory_documents_uploaded': docs.filter(is_mandatory=True).count()
        }
    
    def get_academic_records(self, obj):
        """Get academic performance summary"""
        records = obj.academic_records.all().order_by('-academic_year', '-semester')
        return [{
            'academic_year': record.academic_year,
            'semester': record.semester,
            'gpa': record.gpa,
            'total_credits': record.total_credits,
            'attendance_percentage': record.attendance_percentage
        } for record in records[:4]]  # Last 4 semesters


# Utility Serializers for Choices and Options
class ScholarshipTypeChoicesSerializer(serializers.Serializer):
    """Serializer for scholarship type choices"""
    
    scholarship_types = serializers.ListField(
        child=serializers.DictField(),
        read_only=True
    )
    
    def to_representation(self, instance):
        return {
            'scholarship_types': [
                {'value': choice[0], 'label': choice[1]}
                for choice in ScholarshipApplication.SCHOLARSHIP_TYPES
            ]
        }


class ApplicationStatusChoicesSerializer(serializers.Serializer):
    """Serializer for application status choices"""
    
    status_choices = serializers.ListField(
        child=serializers.DictField(),
        read_only=True
    )
    
    def to_representation(self, instance):
        return {
            'status_choices': [
                {'value': choice[0], 'label': choice[1]}
                for choice in ScholarshipApplication.APPLICATION_STATUS
            ]
        }


class PriorityChoicesSerializer(serializers.Serializer):
    """Serializer for priority level choices"""
    
    priority_choices = serializers.ListField(
        child=serializers.DictField(),
        read_only=True
    )
    
    def to_representation(self, instance):
        return {
            'priority_choices': [
                {'value': choice[0], 'label': choice[1]}
                for choice in ScholarshipApplication.PRIORITY_LEVELS
            ]
        }
