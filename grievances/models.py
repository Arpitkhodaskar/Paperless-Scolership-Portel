from django.db import models
from authentication.models import CustomUser
from students.models import Student
from institutes.models import Institute
from departments.models import Department


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
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'grievance_categories'
        ordering = ['name']


class Grievance(models.Model):
    """Model for student grievances"""
    
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
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('escalated', 'Escalated'),
        ('rejected', 'Rejected'),
    )
    
    grievance_id = models.CharField(max_length=20, unique=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grievances')
    category = models.ForeignKey(GrievanceCategory, on_delete=models.CASCADE, related_name='grievances')
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='grievances')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='grievances')
    subject = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    
    # Assignment and tracking
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_grievances')
    assigned_at = models.DateTimeField(blank=True, null=True)
    
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
    
    # Escalation
    escalated_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='escalated_grievances')
    escalation_reason = models.TextField(blank=True, null=True)
    escalation_date = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Expected resolution date based on category
    expected_resolution_date = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.grievance_id} - {self.subject}"
    
    def save(self, *args, **kwargs):
        if not self.expected_resolution_date and self.category:
            from datetime import timedelta
            self.expected_resolution_date = self.submitted_at + timedelta(days=self.category.resolution_time_days)
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'grievances'
        ordering = ['-submitted_at']


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
