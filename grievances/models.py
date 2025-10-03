from django.db import models
from authentication.models import CustomUser
from students.models import Student
from institutes.models import Institute
from departments.models import Department
from django.utils import timezone
from django.core.validators import MinLengthValidator
import uuid


class GrievanceCategory(models.Model):
    """Categories for different types of grievances"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    priority_level = models.IntegerField(choices=[
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical'),
    ], default=2)
    resolution_time_days = models.IntegerField(default=7)  # Expected resolution time
    
    # Email notification settings
    notify_on_creation = models.BooleanField(default=True)
    notify_on_status_change = models.BooleanField(default=True)
    notification_emails = models.TextField(
        blank=True, 
        help_text="Comma-separated list of email addresses to notify for this category"
    )
    
    # SLA settings
    first_response_time_hours = models.IntegerField(default=24)
    escalation_time_hours = models.IntegerField(default=48)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    @property
    def notification_email_list(self):
        """Get list of notification emails"""
        if self.notification_emails:
            return [email.strip() for email in self.notification_emails.split(',')]
        return []
    
    class Meta:
        db_table = 'grievance_categories'
        ordering = ['name']


class Grievance(models.Model):
    """Model for student grievances with enhanced tracking"""
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    
    STATUS_CHOICES = (
        ('submitted', 'Submitted'),
        ('acknowledged', 'Acknowledged'),
        ('under_review', 'Under Review'),
        ('investigating', 'Investigating'),
        ('pending_user', 'Pending User Response'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('escalated', 'Escalated'),
        ('rejected', 'Rejected'),
    )
    
    # Add UUID for better tracking
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grievance_id = models.CharField(max_length=20, unique=True)
    
    # Basic information
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grievances')
    category = models.ForeignKey(GrievanceCategory, on_delete=models.CASCADE, related_name='grievances')
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='grievances')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='grievances')
    
    # Grievance details
    subject = models.CharField(max_length=200)
    description = models.TextField(validators=[MinLengthValidator(10)])
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    
    # Related references
    application_reference = models.CharField(max_length=100, blank=True, help_text="Related application ID")
    payment_reference = models.CharField(max_length=100, blank=True, help_text="Related payment ID")
    
    # Assignment and tracking
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_grievances')
    assigned_at = models.DateTimeField(blank=True, null=True)
    
    # Response tracking
    first_response_at = models.DateTimeField(blank=True, null=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    
    # Resolution tracking
    resolved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_grievances')
    resolution_date = models.DateTimeField(blank=True, null=True)
    resolution_summary = models.TextField(blank=True, null=True)
    
    # Satisfaction and feedback
    satisfaction_rating = models.IntegerField(choices=[
        (1, '1 - Very Dissatisfied'),
        (2, '2 - Dissatisfied'),
        (3, '3 - Neutral'),
        (4, '4 - Satisfied'),
        (5, '5 - Very Satisfied'),
    ], blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    feedback_submitted_at = models.DateTimeField(blank=True, null=True)
    
    # Escalation
    escalated_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='escalated_grievances')
    escalation_reason = models.TextField(blank=True, null=True)
    escalation_date = models.DateTimeField(blank=True, null=True)
    
    # SLA tracking
    due_date = models.DateTimeField(blank=True, null=True)
    is_overdue = models.BooleanField(default=False)
    
    # Notification tracking
    email_notifications_sent = models.JSONField(default=list, blank=True)
    last_notification_sent = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Expected resolution date based on category
    expected_resolution_date = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.grievance_id} - {self.subject}"
    
    def save(self, *args, **kwargs):
        # Generate grievance ID if not exists
        if not self.grievance_id:
            self.grievance_id = self.generate_grievance_id()
        
        # Set due date and expected resolution date
        if not self.due_date and self.category:
            from datetime import timedelta
            self.due_date = timezone.now() + timedelta(hours=self.category.escalation_time_hours)
            self.expected_resolution_date = self.submitted_at + timedelta(days=self.category.resolution_time_days)
        
        # Update overdue status
        if self.due_date and self.status not in ['resolved', 'closed']:
            self.is_overdue = timezone.now() > self.due_date
        
        super().save(*args, **kwargs)
    
    def generate_grievance_id(self):
        """Generate unique grievance ID"""
        import random
        import string
        
        # Format: GRV-YYYYMMDD-XXXX
        date_part = timezone.now().strftime('%Y%m%d')
        random_part = ''.join(random.choices(string.digits, k=4))
        return f"GRV-{date_part}-{random_part}"
    
    def mark_acknowledged(self, acknowledged_by):
        """Mark grievance as acknowledged"""
        self.status = 'acknowledged'
        if not self.first_response_at:
            self.first_response_at = timezone.now()
        self.assigned_to = acknowledged_by
        self.assigned_at = timezone.now()
        self.save()
    
    def mark_resolved(self, resolution_summary, resolved_by):
        """Mark grievance as resolved"""
        self.status = 'resolved'
        self.resolution_summary = resolution_summary
        self.resolution_date = timezone.now()
        self.resolved_by = resolved_by
        self.is_overdue = False
        self.save()
    
    def escalate_grievance(self, escalated_to, reason):
        """Escalate grievance to higher authority"""
        self.status = 'escalated'
        self.escalated_to = escalated_to
        self.escalation_reason = reason
        self.escalation_date = timezone.now()
        self.priority = 'high'  # Escalated grievances get high priority
        self.save()
    
    def add_notification_sent(self, notification_type, recipient):
        """Track sent notifications"""
        notification_entry = {
            'type': notification_type,
            'recipient': recipient,
            'sent_at': timezone.now().isoformat()
        }
        self.email_notifications_sent.append(notification_entry)
        self.last_notification_sent = timezone.now()
        self.save(update_fields=['email_notifications_sent', 'last_notification_sent'])
    
    @property
    def response_time_hours(self):
        """Calculate response time in hours"""
        if self.first_response_at:
            return (self.first_response_at - self.submitted_at).total_seconds() / 3600
        return None
    
    @property
    def resolution_time_hours(self):
        """Calculate resolution time in hours"""
        if self.resolution_date:
            return (self.resolution_date - self.submitted_at).total_seconds() / 3600
        return None
    
    @property
    def is_sla_breached(self):
        """Check if SLA is breached"""
        if not self.first_response_at and self.category.first_response_time_hours:
            hours_since_submission = (timezone.now() - self.submitted_at).total_seconds() / 3600
            return hours_since_submission > self.category.first_response_time_hours
        return False
    
    class Meta:
        db_table = 'grievances'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['grievance_id']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['is_overdue']),
        ]


class GrievanceComment(models.Model):
    """Comments and updates on grievances"""
    
    COMMENT_TYPES = (
        ('comment', 'Comment'),
        ('status_update', 'Status Update'),
        ('internal_note', 'Internal Note'),
        ('resolution', 'Resolution'),
        ('escalation', 'Escalation'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='comments')
    comment_type = models.CharField(max_length=20, choices=COMMENT_TYPES, default='comment')
    content = models.TextField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='grievance_comments')
    
    # Visibility settings
    is_internal = models.BooleanField(default=False)  # Internal notes not visible to students
    is_visible_to_student = models.BooleanField(default=True)
    is_system_generated = models.BooleanField(default=False)
    
    # Status tracking
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    
    # Email notification
    email_notification_sent = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.grievance.grievance_id} - {self.comment_type}"
    
    def save(self, *args, **kwargs):
        # Update first response time if this is the first staff response
        if (self.created_by.is_staff and 
            not self.grievance.first_response_at and 
            not self.is_internal and
            self.comment_type != 'internal_note'):
            self.grievance.first_response_at = timezone.now()
            self.grievance.save(update_fields=['first_response_at'])
        
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'grievance_comments'
        ordering = ['created_at']


class GrievanceDocument(models.Model):
    """Documents attached to grievances"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='documents')
    comment = models.ForeignKey(GrievanceComment, on_delete=models.CASCADE, related_name='documents', blank=True, null=True)
    
    document_name = models.CharField(max_length=200)
    document_file = models.FileField(upload_to='grievance_documents/%Y/%m/')
    file_size = models.PositiveIntegerField(blank=True, null=True)
    file_type = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True, null=True)
    
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='uploaded_grievance_documents')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.grievance.grievance_id} - {self.document_name}"
    
    def save(self, *args, **kwargs):
        if self.document_file:
            self.file_size = self.document_file.size
            self.file_type = self.document_file.name.split('.')[-1].lower()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'grievance_documents'
        ordering = ['-uploaded_at']


class GrievanceAdmin(models.Model):
    """Model for grievance administrators"""
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='grievance_admin_profile')
    employee_id = models.CharField(max_length=20, unique=True)
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='grievance_admins', blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='grievance_admins')
    designation = models.CharField(max_length=100)
    categories_handled = models.ManyToManyField(GrievanceCategory, blank=True)
    
    # Enhanced permissions
    permissions = models.JSONField(default=dict, blank=True)  # Store specific permissions
    can_escalate = models.BooleanField(default=True)
    can_resolve = models.BooleanField(default=True)
    can_reassign = models.BooleanField(default=True)
    max_priority_level = models.IntegerField(default=3)  # Maximum priority level they can handle
    
    # Settings
    email_notifications_enabled = models.BooleanField(default=True)
    auto_assignment_enabled = models.BooleanField(default=True)
    
    is_primary_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Grievance Admin"
    
    class Meta:
        db_table = 'grievance_admins'


class GrievanceStatusLog(models.Model):
    """Log of status changes for grievances"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='status_logs')
    previous_status = models.CharField(max_length=20, blank=True, null=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='grievance_status_changes')
    change_reason = models.TextField(blank=True, null=True)
    
    # Additional tracking
    time_in_previous_status_hours = models.FloatField(blank=True, null=True)
    automated_change = models.BooleanField(default=False)
    
    changed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.grievance.grievance_id} - {self.previous_status} to {self.new_status}"
    
    class Meta:
        db_table = 'grievance_status_logs'
        ordering = ['-changed_at']


class FAQ(models.Model):
    """Frequently Asked Questions for common grievances"""
    
    question = models.CharField(max_length=500)
    answer = models.TextField()
    category = models.ForeignKey(GrievanceCategory, on_delete=models.CASCADE, related_name='faqs')
    tags = models.JSONField(default=list, blank=True)  # For better searchability
    
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # Analytics
    view_count = models.PositiveIntegerField(default=0)
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)
    
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_faqs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.question[:100]
    
    @property
    def helpfulness_score(self):
        """Calculate helpfulness score"""
        total_votes = self.helpful_count + self.not_helpful_count
        if total_votes == 0:
            return 0
        return (self.helpful_count / total_votes) * 100
    
    class Meta:
        db_table = 'faqs'
        ordering = ['-is_featured', '-helpful_count', '-view_count', '-created_at']


class GrievanceTemplate(models.Model):
    """Response templates for common grievance types"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(GrievanceCategory, on_delete=models.CASCADE, related_name='templates')
    
    # Template content
    subject = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    
    # Usage
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    usage_count = models.PositiveIntegerField(default=0)
    
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.category.name}"
    
    class Meta:
        db_table = 'grievance_templates'
        ordering = ['category__name', 'name']


class GrievanceNotificationLog(models.Model):
    """Log of all notifications sent for grievances"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='notification_logs')
    
    # Notification details
    notification_type = models.CharField(max_length=50)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=200)
    content = models.TextField()
    
    # Status
    sent_successfully = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Notification for {self.grievance.grievance_id} to {self.recipient_email}"
    
    class Meta:
        db_table = 'grievance_notification_logs'
        ordering = ['-sent_at']


class GrievanceComment(models.Model):
    """Comments and updates on grievances"""
    
    COMMENT_TYPES = (
        ('comment', 'Comment'),
        ('status_update', 'Status Update'),
        ('internal_note', 'Internal Note'),
        ('resolution', 'Resolution'),
    )
    
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='comments')
    comment_type = models.CharField(max_length=20, choices=COMMENT_TYPES, default='comment')
    content = models.TextField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='grievance_comments')
    is_internal = models.BooleanField(default=False)  # Internal notes not visible to students
    is_visible_to_student = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.grievance.grievance_id} - {self.comment_type}"
    
    class Meta:
        db_table = 'grievance_comments'
        ordering = ['created_at']


class GrievanceDocument(models.Model):
    """Documents attached to grievances"""
    
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='documents')
    document_name = models.CharField(max_length=200)
    document_file = models.FileField(upload_to='grievance_documents/')
    description = models.TextField(blank=True, null=True)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='uploaded_grievance_documents')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.grievance.grievance_id} - {self.document_name}"
    
    class Meta:
        db_table = 'grievance_documents'
        ordering = ['-uploaded_at']


class GrievanceAdmin(models.Model):
    """Model for grievance administrators"""
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='grievance_admin_profile')
    employee_id = models.CharField(max_length=20, unique=True)
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='grievance_admins', blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='grievance_admins')
    designation = models.CharField(max_length=100)
    categories_handled = models.ManyToManyField(GrievanceCategory, blank=True)
    permissions = models.JSONField(default=dict, blank=True)  # Store specific permissions
    is_primary_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Grievance Admin"
    
    class Meta:
        db_table = 'grievance_admins'


class GrievanceStatusLog(models.Model):
    """Log of status changes for grievances"""
    
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='status_logs')
    previous_status = models.CharField(max_length=20, blank=True, null=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='grievance_status_changes')
    change_reason = models.TextField(blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.grievance.grievance_id} - {self.previous_status} to {self.new_status}"
    
    class Meta:
        db_table = 'grievance_status_logs'
        ordering = ['-changed_at']


class FAQ(models.Model):
    """Frequently Asked Questions for common grievances"""
    
    question = models.CharField(max_length=500)
    answer = models.TextField()
    category = models.ForeignKey(GrievanceCategory, on_delete=models.CASCADE, related_name='faqs')
    is_active = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_faqs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.question[:100]
    
    class Meta:
        db_table = 'faqs'
        ordering = ['-view_count', '-created_at']
