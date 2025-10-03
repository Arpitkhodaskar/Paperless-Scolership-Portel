"""
Department Module Serializers
Comprehensive serializers for Department administration
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Avg
from django.utils import timezone
import json

from .models import Department, DepartmentAdmin, Course, Subject, Faculty
from students.models import Student, ScholarshipApplication, StudentDocument
from institutes.models import Institute
from authentication.models import CustomUser

User = get_user_model()


class DepartmentBasicSerializer(serializers.ModelSerializer):
    """Basic department information serializer"""
    
    institute_name = serializers.CharField(source='institute.name', read_only=True)
    
    class Meta:
        model = Department
        fields = [
            'id', 'name', 'code', 'institute', 'institute_name',
            'department_type', 'head_of_department', 'is_active'
        ]


class DepartmentSerializer(serializers.ModelSerializer):
    """Complete department serializer"""
    
    institute_name = serializers.CharField(source='institute.name', read_only=True)
    total_students = serializers.SerializerMethodField()
    total_courses = serializers.SerializerMethodField()
    total_faculty = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = [
            'id', 'name', 'code', 'institute', 'institute_name',
            'department_type', 'description', 'head_of_department',
            'hod_email', 'hod_phone', 'office_location', 'office_phone',
            'office_email', 'established_year', 'is_active',
            'total_students', 'total_courses', 'total_faculty',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_students(self, obj):
        return obj.students.filter(is_active=True).count()
    
    def get_total_courses(self, obj):
        return obj.courses.filter(is_active=True).count()
    
    def get_total_faculty(self, obj):
        return obj.faculty.filter(is_active=True).count()


class DepartmentDetailSerializer(DepartmentSerializer):
    """Detailed department serializer with related data"""
    
    courses = serializers.SerializerMethodField()
    recent_applications = serializers.SerializerMethodField()
    admin_users = serializers.SerializerMethodField()
    
    class Meta(DepartmentSerializer.Meta):
        fields = DepartmentSerializer.Meta.fields + [
            'courses', 'recent_applications', 'admin_users'
        ]
    
    def get_courses(self, obj):
        courses = obj.courses.filter(is_active=True)[:5]
        return [{
            'id': course.id,
            'name': course.name,
            'code': course.code,
            'course_type': course.course_type,
            'total_seats': course.total_seats
        } for course in courses]
    
    def get_recent_applications(self, obj):
        recent_apps = ScholarshipApplication.objects.filter(
            student__department=obj
        ).select_related('student', 'student__user').order_by('-submitted_at')[:5]
        
        return [{
            'application_id': app.application_id,
            'student_name': app.student.user.get_full_name(),
            'scholarship_type': app.scholarship_type,
            'amount_requested': app.amount_requested,
            'status': app.status,
            'submitted_at': app.submitted_at
        } for app in recent_apps]
    
    def get_admin_users(self, obj):
        admins = obj.admins.filter(user__is_active=True)
        return [{
            'id': admin.id,
            'user_name': admin.user.get_full_name(),
            'user_email': admin.user.email,
            'designation': admin.designation,
            'is_primary_admin': admin.is_primary_admin
        } for admin in admins]


class DepartmentAdminSerializer(serializers.ModelSerializer):
    """Department admin serializer"""
    
    user_details = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    
    class Meta:
        model = DepartmentAdmin
        fields = [
            'id', 'user', 'user_details', 'department', 'department_name',
            'designation', 'employee_id', 'is_primary_admin', 'permissions',
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


class StudentBasicInfoSerializer(serializers.ModelSerializer):
    """Basic student information for application lists"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    institute_name = serializers.CharField(source='institute.name', read_only=True)
    
    class Meta:
        model = Student
        fields = [
            'id', 'student_id', 'user_name', 'user_email', 'institute_name',
            'course_level', 'course_name', 'academic_year', 'cgpa',
            'is_active', 'is_verified', 'enrollment_date'
        ]


class VerifiedApplicationListSerializer(serializers.ModelSerializer):
    """Serializer for listing verified applications for department review"""
    
    student_details = StudentBasicInfoSerializer(source='student', read_only=True)
    institute_name = serializers.CharField(source='student.institute.name', read_only=True)
    department_status = serializers.SerializerMethodField()
    days_since_institute_approval = serializers.SerializerMethodField()
    is_forwarded_to_finance = serializers.SerializerMethodField()
    processing_priority = serializers.SerializerMethodField()
    
    class Meta:
        model = ScholarshipApplication
        fields = [
            'id', 'application_id', 'student_details', 'institute_name',
            'scholarship_type', 'scholarship_name', 'amount_requested',
            'amount_approved', 'status', 'priority', 'reason',
            'submitted_at', 'approved_at', 'department_status',
            'days_since_institute_approval', 'is_forwarded_to_finance',
            'processing_priority', 'eligibility_score', 'document_completeness_score'
        ]
    
    def get_department_status(self, obj):
        """Determine department processing status"""
        if obj.internal_notes:
            if 'DEPT_APPROVED' in obj.internal_notes:
                if 'FORWARDED_TO_FINANCE' in obj.internal_notes:
                    return 'forwarded_to_finance'
                return 'dept_approved'
            elif 'DEPT_REJECTED' in obj.internal_notes:
                return 'dept_rejected'
        return 'pending_review'
    
    def get_days_since_institute_approval(self, obj):
        """Calculate days since institute approval"""
        if obj.approved_at:
            return (timezone.now() - obj.approved_at).days
        return 0
    
    def get_is_forwarded_to_finance(self, obj):
        """Check if application is forwarded to finance"""
        return obj.internal_notes and 'FORWARDED_TO_FINANCE' in obj.internal_notes
    
    def get_processing_priority(self, obj):
        """Determine processing priority based on various factors"""
        priority_score = 0
        
        # Base priority
        priority_map = {'urgent': 4, 'high': 3, 'medium': 2, 'low': 1}
        priority_score += priority_map.get(obj.priority, 2)
        
        # Days since approval
        if obj.approved_at:
            days_since = (timezone.now() - obj.approved_at).days
            if days_since > 7:
                priority_score += 2
            elif days_since > 3:
                priority_score += 1
        
        # Amount factor
        if obj.amount_approved and obj.amount_approved > 75000:
            priority_score += 1
        
        if priority_score >= 6:
            return 'urgent'
        elif priority_score >= 4:
            return 'high'
        elif priority_score >= 2:
            return 'medium'
        else:
            return 'low'


class ApplicationReviewSerializer(serializers.Serializer):
    """Serializer for department application review"""
    
    ACTION_CHOICES = [
        ('dept_approve', 'Department Approve'),
        ('dept_reject', 'Department Reject'),
    ]
    
    action = serializers.ChoiceField(choices=ACTION_CHOICES, required=True)
    dept_remarks = serializers.CharField(max_length=1000, required=True, 
                                        help_text="Department remarks for the decision")
    internal_notes = serializers.CharField(max_length=2000, required=False, allow_blank=True,
                                          help_text="Internal notes for department reference")
    final_approved_amount = serializers.DecimalField(max_digits=10, decimal_places=2, 
                                                     required=False, allow_null=True,
                                                     help_text="Final approved amount (for approve action)")
    
    def validate(self, data):
        action = data.get('action')
        final_approved_amount = data.get('final_approved_amount')
        
        if action == 'dept_approve' and final_approved_amount is not None:
            if final_approved_amount <= 0:
                raise serializers.ValidationError("Final approved amount must be greater than 0")
        
        return data


class ApplicationForwardSerializer(serializers.Serializer):
    """Serializer for forwarding applications to finance"""
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    application_ids = serializers.ListField(
        child=serializers.CharField(max_length=30),
        min_length=1,
        max_length=25,
        help_text="List of application IDs to forward to finance"
    )
    forward_remarks = serializers.CharField(max_length=1000, required=True,
                                           help_text="Remarks for finance team")
    priority = serializers.ChoiceField(choices=PRIORITY_CHOICES, default='medium',
                                      help_text="Priority for finance processing")
    
    def validate_application_ids(self, value):
        """Validate that all application IDs are valid"""
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Duplicate application IDs found")
        return value


class ApplicationDecisionSerializer(serializers.ModelSerializer):
    """Serializer for application decision response"""
    
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    department_status = serializers.SerializerMethodField()
    
    class Meta:
        model = ScholarshipApplication
        fields = [
            'id', 'application_id', 'student_name', 'scholarship_type',
            'amount_requested', 'amount_approved', 'status', 'priority',
            'department_status', 'review_comments', 'rejection_reason',
            'updated_at'
        ]
    
    def get_department_status(self, obj):
        """Get department processing status"""
        if obj.internal_notes:
            if 'DEPT_APPROVED' in obj.internal_notes:
                return 'dept_approved'
            elif 'DEPT_REJECTED' in obj.internal_notes:
                return 'dept_rejected'
        return 'pending_review'


class ForwardedApplicationTrackingSerializer(serializers.Serializer):
    """Serializer for tracking forwarded applications"""
    
    application_id = serializers.CharField()
    student_name = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    forwarded_at = serializers.DateTimeField()
    priority = serializers.CharField()
    forwarded_by = serializers.EmailField()
    finance_status = serializers.CharField(default='pending_finance_review')


class DepartmentDashboardSerializer(serializers.Serializer):
    """Serializer for department dashboard data"""
    
    department_name = serializers.CharField()
    department_code = serializers.CharField()
    generated_at = serializers.DateTimeField()
    
    # Key metrics
    key_metrics = serializers.DictField()
    
    # Charts and analytics
    charts = serializers.DictField()
    
    # Recent activities
    recent_activities = serializers.ListField(child=serializers.DictField())
    
    # Alerts and notifications
    alerts = serializers.DictField()


class DepartmentReportSerializer(serializers.Serializer):
    """Serializer for department reports"""
    
    report_type = serializers.CharField()
    department = serializers.CharField()
    generated_at = serializers.DateTimeField()
    
    # Summary report fields
    total_applications = serializers.IntegerField(required=False)
    dept_approved = serializers.IntegerField(required=False)
    dept_rejected = serializers.IntegerField(required=False)
    forwarded_to_finance = serializers.IntegerField(required=False)
    pending_review = serializers.IntegerField(required=False)
    approval_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    total_approved_amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    average_approved_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    
    # Detailed report fields
    total_records = serializers.IntegerField(required=False)
    applications = serializers.ListField(child=serializers.DictField(), required=False)
    
    # Financial report fields
    financial_summary = serializers.DictField(required=False)
    amount_range_analysis = serializers.ListField(child=serializers.DictField(), required=False)
    
    # Performance report fields
    processing_efficiency = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    total_processed = serializers.IntegerField(required=False)
    pending_processing = serializers.IntegerField(required=False)
    avg_processing_time = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    
    # Course-wise report fields
    course_analysis = serializers.ListField(child=serializers.DictField(), required=False)
    
    # Forwarded tracking fields
    total_forwarded = serializers.IntegerField(required=False)
    forwarded_applications = serializers.ListField(child=ForwardedApplicationTrackingSerializer(), required=False)


class DepartmentStatisticsSerializer(serializers.Serializer):
    """Serializer for department statistics"""
    
    # Student statistics
    total_students = serializers.IntegerField()
    active_students = serializers.IntegerField()
    verified_students = serializers.IntegerField()
    students_by_year = serializers.ListField(child=serializers.DictField())
    
    # Application statistics
    total_applications = serializers.IntegerField()
    institute_approved_applications = serializers.IntegerField()
    dept_approved_applications = serializers.IntegerField()
    dept_rejected_applications = serializers.IntegerField()
    forwarded_applications = serializers.IntegerField()
    pending_dept_review = serializers.IntegerField()
    
    # Financial statistics
    total_amount_requested = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_amount_approved = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_amount_forwarded = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Performance metrics
    dept_approval_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    avg_processing_time = serializers.DecimalField(max_digits=5, decimal_places=2)
    processing_efficiency = serializers.DecimalField(max_digits=5, decimal_places=2)


class CourseSerializer(serializers.ModelSerializer):
    """Course serializer for department"""
    
    department_name = serializers.CharField(source='department.name', read_only=True)
    total_students = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'name', 'code', 'department', 'department_name',
            'course_type', 'duration_years', 'duration_semesters',
            'total_seats', 'fee_per_semester', 'description',
            'eligibility_criteria', 'is_active', 'total_students'
        ]
    
    def get_total_students(self, obj):
        return obj.department.students.filter(
            course_name__icontains=obj.name,
            is_active=True
        ).count()


class SubjectSerializer(serializers.ModelSerializer):
    """Subject serializer for courses"""
    
    course_name = serializers.CharField(source='course.name', read_only=True)
    
    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'code', 'course', 'course_name',
            'subject_type', 'credits', 'semester', 'description',
            'syllabus', 'is_active'
        ]


class FacultySerializer(serializers.ModelSerializer):
    """Faculty serializer for department"""
    
    user_details = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    
    class Meta:
        model = Faculty
        fields = [
            'id', 'user', 'user_details', 'employee_id', 'department',
            'department_name', 'designation', 'qualification',
            'specialization', 'experience_years', 'joining_date',
            'office_hours', 'research_interests', 'is_active'
        ]
    
    def get_user_details(self, obj):
        return {
            'email': obj.user.email,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'full_name': obj.user.get_full_name(),
            'phone_number': obj.user.phone_number
        }


class ApplicationWorkflowSerializer(serializers.Serializer):
    """Serializer for application workflow tracking"""
    
    application_id = serializers.CharField()
    student_name = serializers.CharField()
    current_status = serializers.CharField()
    workflow_stages = serializers.ListField(child=serializers.DictField())
    department_actions = serializers.ListField(child=serializers.DictField())
    next_actions = serializers.ListField(child=serializers.CharField())


class BulkActionResponseSerializer(serializers.Serializer):
    """Serializer for bulk action responses"""
    
    message = serializers.CharField()
    processed_count = serializers.IntegerField()
    failed_items = serializers.ListField(child=serializers.DictField())
    success_items = serializers.ListField(child=serializers.CharField())


# Utility Serializers
class DepartmentChoicesSerializer(serializers.Serializer):
    """Serializer for department-related choices"""
    
    scholarship_types = serializers.ListField(child=serializers.DictField(), read_only=True)
    priority_levels = serializers.ListField(child=serializers.DictField(), read_only=True)
    course_types = serializers.ListField(child=serializers.DictField(), read_only=True)
    
    def to_representation(self, instance):
        from students.models import ScholarshipApplication
        
        return {
            'scholarship_types': [
                {'value': choice[0], 'label': choice[1]}
                for choice in ScholarshipApplication.SCHOLARSHIP_TYPES
            ],
            'priority_levels': [
                {'value': choice[0], 'label': choice[1]}
                for choice in ScholarshipApplication.PRIORITY_LEVELS
            ],
            'course_types': [
                {'value': choice[0], 'label': choice[1]}
                for choice in Course.COURSE_TYPES
            ]
        }


class DepartmentPermissionsSerializer(serializers.Serializer):
    """Serializer for department admin permissions"""
    
    can_review_applications = serializers.BooleanField(default=True)
    can_approve_applications = serializers.BooleanField(default=True)
    can_reject_applications = serializers.BooleanField(default=True)
    can_forward_to_finance = serializers.BooleanField(default=True)
    can_generate_reports = serializers.BooleanField(default=True)
    can_manage_students = serializers.BooleanField(default=False)
    can_manage_courses = serializers.BooleanField(default=False)
    can_manage_faculty = serializers.BooleanField(default=False)
    can_manage_department_settings = serializers.BooleanField(default=False)
    
    def validate(self, data):
        """Validate permission combinations"""
        # Basic validation logic
        if not any([
            data.get('can_review_applications'),
            data.get('can_generate_reports')
        ]):
            raise serializers.ValidationError(
                "At least one of review applications or generate reports permission must be enabled"
            )
        
        return data
