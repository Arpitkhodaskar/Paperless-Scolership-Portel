from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Grievance, GrievanceCategory, GrievanceComment, GrievanceDocument,
    GrievanceAdmin, GrievanceStatusLog, FAQ, GrievanceTemplate,
    GrievanceNotificationLog
)


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer"""
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'full_name']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class GrievanceCategorySerializer(serializers.ModelSerializer):
    """Serializer for grievance categories"""
    
    class Meta:
        model = GrievanceCategory
        fields = [
            'id', 'name', 'description', 'priority_level', 'resolution_time_days',
            'first_response_time_hours', 'escalation_time_hours', 'is_active'
        ]


class GrievanceDocumentSerializer(serializers.ModelSerializer):
    """Serializer for grievance documents"""
    
    uploaded_by = UserSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = GrievanceDocument
        fields = [
            'id', 'document_name', 'document_file', 'file_url', 'file_size',
            'file_type', 'description', 'uploaded_by', 'uploaded_at'
        ]
    
    def get_file_url(self, obj):
        if obj.document_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.document_file.url)
        return None


class GrievanceCommentSerializer(serializers.ModelSerializer):
    """Serializer for grievance comments"""
    
    created_by = UserSerializer(read_only=True)
    documents = GrievanceDocumentSerializer(many=True, read_only=True)
    time_since_creation = serializers.SerializerMethodField()
    
    class Meta:
        model = GrievanceComment
        fields = [
            'id', 'comment_type', 'content', 'created_by', 'is_internal',
            'is_visible_to_student', 'is_system_generated', 'previous_status',
            'new_status', 'created_at', 'time_since_creation', 'documents'
        ]
    
    def get_time_since_creation(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.created_at
        
        if delta.days > 0:
            return f"{delta.days} days ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours} hours ago"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes} minutes ago"
        else:
            return "Just now"


class GrievanceStatusLogSerializer(serializers.ModelSerializer):
    """Serializer for grievance status logs"""
    
    changed_by = UserSerializer(read_only=True)
    
    class Meta:
        model = GrievanceStatusLog
        fields = [
            'id', 'previous_status', 'new_status', 'changed_by', 'change_reason',
            'time_in_previous_status_hours', 'automated_change', 'changed_at'
        ]


class GrievanceSerializer(serializers.ModelSerializer):
    """Basic grievance serializer"""
    
    category = GrievanceCategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    assigned_to = UserSerializer(read_only=True)
    resolved_by = UserSerializer(read_only=True)
    escalated_to = UserSerializer(read_only=True)
    
    # Student information
    student_name = serializers.SerializerMethodField()
    student_email = serializers.SerializerMethodField()
    
    # Calculated fields
    time_since_submission = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()
    
    # Counts
    comments_count = serializers.SerializerMethodField()
    documents_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Grievance
        fields = [
            'id', 'grievance_id', 'category', 'category_id', 'subject', 'description',
            'priority', 'priority_display', 'status', 'status_display', 'assigned_to',
            'assigned_at', 'resolved_by', 'resolution_date', 'resolution_summary',
            'escalated_to', 'escalation_reason', 'escalation_date', 'satisfaction_rating',
            'feedback', 'feedback_submitted_at', 'due_date', 'is_overdue',
            'submitted_at', 'updated_at', 'expected_resolution_date',
            'student_name', 'student_email', 'time_since_submission',
            'comments_count', 'documents_count', 'response_time_hours',
            'resolution_time_hours', 'is_sla_breached'
        ]
        read_only_fields = [
            'id', 'grievance_id', 'submitted_at', 'updated_at', 'is_overdue',
            'response_time_hours', 'resolution_time_hours', 'is_sla_breached'
        ]
    
    def get_student_name(self, obj):
        return obj.student.user.get_full_name() or obj.student.user.username
    
    def get_student_email(self, obj):
        return obj.student.user.email
    
    def get_time_since_submission(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.submitted_at
        
        if delta.days > 0:
            return f"{delta.days} days ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours} hours ago"
        else:
            minutes = delta.seconds // 60
            return f"{minutes} minutes ago"
    
    def get_status_display(self, obj):
        return obj.get_status_display()
    
    def get_priority_display(self, obj):
        return obj.get_priority_display()
    
    def get_comments_count(self, obj):
        return obj.comments.count()
    
    def get_documents_count(self, obj):
        return obj.documents.count()


class GrievanceDetailSerializer(GrievanceSerializer):
    """Detailed grievance serializer with related objects"""
    
    comments = GrievanceCommentSerializer(many=True, read_only=True)
    documents = GrievanceDocumentSerializer(many=True, read_only=True)
    status_logs = GrievanceStatusLogSerializer(many=True, read_only=True)
    
    # Institute and department info
    institute_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    
    class Meta(GrievanceSerializer.Meta):
        fields = GrievanceSerializer.Meta.fields + [
            'comments', 'documents', 'status_logs', 'institute_name',
            'department_name', 'application_reference', 'payment_reference',
            'first_response_at', 'last_activity_at'
        ]
    
    def get_institute_name(self, obj):
        return obj.institute.name if obj.institute else None
    
    def get_department_name(self, obj):
        return obj.department.name if obj.department else None


class GrievanceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating grievances"""
    
    class Meta:
        model = Grievance
        fields = [
            'category', 'subject', 'description', 'priority',
            'application_reference', 'payment_reference'
        ]
    
    def validate_description(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Description must be at least 10 characters long.")
        return value


class FAQSerializer(serializers.ModelSerializer):
    """Serializer for FAQs"""
    
    category = GrievanceCategorySerializer(read_only=True)
    helpfulness_score = serializers.ReadOnlyField()
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = FAQ
        fields = [
            'id', 'question', 'answer', 'category', 'tags', 'is_active',
            'is_featured', 'view_count', 'helpful_count', 'not_helpful_count',
            'helpfulness_score', 'created_by', 'created_at', 'updated_at'
        ]


class GrievanceTemplateSerializer(serializers.ModelSerializer):
    """Serializer for grievance response templates"""
    
    category = GrievanceCategorySerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = GrievanceTemplate
        fields = [
            'id', 'name', 'category', 'subject', 'content', 'is_active',
            'is_default', 'usage_count', 'created_by', 'created_at', 'updated_at'
        ]


class GrievanceStatsSerializer(serializers.Serializer):
    """Serializer for grievance statistics"""
    
    total_grievances = serializers.IntegerField()
    open_grievances = serializers.IntegerField()
    resolved_grievances = serializers.IntegerField()
    overdue_grievances = serializers.IntegerField()
    average_resolution_time = serializers.FloatField()
    category_breakdown = serializers.ListField()
    priority_breakdown = serializers.ListField()
    satisfaction_rating_avg = serializers.FloatField(required=False)
    sla_compliance_rate = serializers.FloatField(required=False)


class GrievanceAdminSerializer(serializers.ModelSerializer):
    """Serializer for grievance administrators"""
    
    user = UserSerializer(read_only=True)
    categories_handled = GrievanceCategorySerializer(many=True, read_only=True)
    
    class Meta:
        model = GrievanceAdmin
        fields = [
            'id', 'user', 'employee_id', 'designation', 'categories_handled',
            'can_escalate', 'can_resolve', 'can_reassign', 'max_priority_level',
            'email_notifications_enabled', 'auto_assignment_enabled',
            'is_primary_admin', 'is_active'
        ]


class GrievanceNotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for notification logs"""
    
    grievance = serializers.StringRelatedField()
    
    class Meta:
        model = GrievanceNotificationLog
        fields = [
            'id', 'grievance', 'notification_type', 'recipient_email',
            'subject', 'sent_successfully', 'error_message', 'sent_at'
        ]


class GrievanceBulkActionSerializer(serializers.Serializer):
    """Serializer for bulk actions on grievances"""
    
    grievance_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )
    action = serializers.ChoiceField(choices=[
        ('assign', 'Assign'),
        ('update_status', 'Update Status'),
        ('update_priority', 'Update Priority'),
        ('add_tag', 'Add Tag'),
    ])
    assigned_to = serializers.IntegerField(required=False)
    status = serializers.CharField(max_length=20, required=False)
    priority = serializers.CharField(max_length=10, required=False)
    tag = serializers.CharField(max_length=50, required=False)
    reason = serializers.CharField(max_length=500, required=False)


class GrievanceEscalationSerializer(serializers.Serializer):
    """Serializer for grievance escalation"""
    
    escalated_to = serializers.IntegerField()
    reason = serializers.CharField(max_length=1000)
    
    def validate_escalated_to(self, value):
        try:
            User.objects.get(id=value, is_staff=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid user ID or user is not staff.")
        return value


class GrievanceFeedbackSerializer(serializers.Serializer):
    """Serializer for grievance satisfaction feedback"""
    
    satisfaction_rating = serializers.IntegerField(min_value=1, max_value=5)
    feedback = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class GrievanceReportSerializer(serializers.Serializer):
    """Serializer for grievance reports"""
    
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    category_id = serializers.IntegerField(required=False)
    status = serializers.CharField(max_length=20, required=False)
    priority = serializers.CharField(max_length=10, required=False)
    assigned_to = serializers.IntegerField(required=False)
    include_resolved = serializers.BooleanField(default=True)
    include_closed = serializers.BooleanField(default=False)
    
    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("Start date must be before end date.")
        return data
