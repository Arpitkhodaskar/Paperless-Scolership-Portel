from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import uuid


class NotificationType(models.TextChoices):
    """Choices for different types of notifications"""
    APPLICATION_SUBMITTED = 'application_submitted', 'Application Submitted'
    APPLICATION_UNDER_REVIEW = 'application_under_review', 'Application Under Review'
    APPLICATION_APPROVED = 'application_approved', 'Application Approved'
    APPLICATION_REJECTED = 'application_rejected', 'Application Rejected'
    PAYMENT_PROCESSED = 'payment_processed', 'Payment Processed'
    PAYMENT_FAILED = 'payment_failed', 'Payment Failed'
    DOCUMENT_REQUIRED = 'document_required', 'Document Required'
    DEADLINE_REMINDER = 'deadline_reminder', 'Deadline Reminder'
    GRIEVANCE_CREATED = 'grievance_created', 'Grievance Created'
    GRIEVANCE_UPDATED = 'grievance_updated', 'Grievance Updated'
    GRIEVANCE_RESOLVED = 'grievance_resolved', 'Grievance Resolved'
    SYSTEM_MAINTENANCE = 'system_maintenance', 'System Maintenance'


class NotificationChannel(models.TextChoices):
    """Channels through which notifications can be sent"""
    EMAIL = 'email', 'Email'
    SMS = 'sms', 'SMS'
    IN_APP = 'in_app', 'In-App'
    PUSH = 'push', 'Push Notification'


class NotificationTemplate(models.Model):
    """Templates for different types of notifications"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        unique=True
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Email template fields
    email_subject = models.CharField(max_length=200, blank=True)
    email_body_text = models.TextField(blank=True, help_text="Plain text email body")
    email_body_html = models.TextField(blank=True, help_text="HTML email body")
    
    # SMS template fields
    sms_body = models.CharField(max_length=160, blank=True, help_text="SMS message body (160 chars max)")
    
    # In-app notification fields
    in_app_title = models.CharField(max_length=100, blank=True)
    in_app_message = models.TextField(blank=True)
    
    # Settings
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification Template"
        verbose_name_plural = "Notification Templates"
    
    def __str__(self):
        return f"{self.name} ({self.get_notification_type_display()})"


class Notification(models.Model):
    """Individual notification instances"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NotificationType.choices)
    channel = models.CharField(max_length=20, choices=NotificationChannel.choices)
    
    # Content
    subject = models.CharField(max_length=200)
    message = models.TextField()
    
    # Status
    is_sent = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    reference_id = models.CharField(max_length=100, blank=True, help_text="Reference to related object ID")
    reference_type = models.CharField(max_length=50, blank=True, help_text="Type of related object")
    metadata = models.JSONField(default=dict, blank=True)
    
    # Tracking
    delivery_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('sent', 'Sent'),
            ('delivered', 'Delivered'),
            ('failed', 'Failed'),
            ('bounced', 'Bounced'),
        ],
        default='pending'
    )
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['delivery_status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.subject} - {self.recipient.username} ({self.get_channel_display()})"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_sent(self):
        """Mark notification as sent"""
        if not self.is_sent:
            self.is_sent = True
            self.sent_at = timezone.now()
            self.delivery_status = 'sent'
            self.save(update_fields=['is_sent', 'sent_at', 'delivery_status'])


class NotificationPreference(models.Model):
    """User preferences for notifications"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Channel preferences
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    in_app_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    
    # Notification type preferences
    application_notifications = models.BooleanField(default=True)
    payment_notifications = models.BooleanField(default=True)
    deadline_notifications = models.BooleanField(default=True)
    grievance_notifications = models.BooleanField(default=True)
    system_notifications = models.BooleanField(default=True)
    
    # Timing preferences
    email_digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate'),
            ('daily', 'Daily Digest'),
            ('weekly', 'Weekly Digest'),
            ('never', 'Never'),
        ],
        default='immediate'
    )
    
    # Contact information
    preferred_email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"
    
    def __str__(self):
        return f"Preferences for {self.user.username}"


class EmailLog(models.Model):
    """Log of all email communications"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.OneToOneField(
        Notification, 
        on_delete=models.CASCADE, 
        related_name='email_log',
        null=True, 
        blank=True
    )
    
    # Email details
    to_email = models.EmailField()
    from_email = models.EmailField()
    subject = models.CharField(max_length=200)
    body_text = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    
    # Status
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivery_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('sent', 'Sent'),
            ('delivered', 'Delivered'),
            ('failed', 'Failed'),
            ('bounced', 'Bounced'),
        ],
        default='pending'
    )
    
    # Error tracking
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    message_id = models.CharField(max_length=200, blank=True)
    headers = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Email Log"
        verbose_name_plural = "Email Logs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Email to {self.to_email}: {self.subject}"


class NotificationBatch(models.Model):
    """Batch processing for bulk notifications"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    notification_type = models.CharField(max_length=50, choices=NotificationType.choices)
    
    # Recipients
    total_recipients = models.PositiveIntegerField(default=0)
    successful_sends = models.PositiveIntegerField(default=0)
    failed_sends = models.PositiveIntegerField(default=0)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
    )
    
    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_notification_batches')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification Batch"
        verbose_name_plural = "Notification Batches"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.status})"
