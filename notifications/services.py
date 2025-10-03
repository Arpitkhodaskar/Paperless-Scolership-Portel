from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.contrib.auth.models import User
from django.utils import timezone
import logging
from typing import Dict, List, Optional, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

from .models import (
    Notification, NotificationTemplate, NotificationPreference, 
    EmailLog, NotificationType, NotificationChannel
)

logger = logging.getLogger(__name__)


class EmailService:
    """Service for handling email notifications"""
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@scholarshipportal.com')
        self.smtp_host = getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'EMAIL_PORT', 587)
        self.smtp_user = getattr(settings, 'EMAIL_HOST_USER', '')
        self.smtp_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        self.use_tls = getattr(settings, 'EMAIL_USE_TLS', True)
    
    def send_notification_email(
        self, 
        user: User, 
        notification_type: str, 
        context: Dict[str, Any] = None,
        attachments: List[str] = None
    ) -> bool:
        """
        Send email notification to user based on notification type
        
        Args:
            user: User to send notification to
            notification_type: Type of notification (from NotificationType choices)
            context: Additional context for email template
            attachments: List of file paths to attach
        
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Check user preferences
            preferences = self.get_user_preferences(user)
            if not preferences.email_enabled:
                logger.info(f"Email notifications disabled for user {user.username}")
                return False
            
            # Get notification template
            template = self.get_notification_template(notification_type)
            if not template:
                logger.error(f"No template found for notification type: {notification_type}")
                return False
            
            # Prepare context
            email_context = self.prepare_email_context(user, context or {})
            
            # Render email content
            subject = self.render_template_string(template.email_subject, email_context)
            text_body = self.render_template_string(template.email_body_text, email_context)
            html_body = self.render_template_string(template.email_body_html, email_context)
            
            # Get recipient email
            recipient_email = self.get_user_email(user, preferences)
            
            # Create notification record
            notification = Notification.objects.create(
                recipient=user,
                notification_type=notification_type,
                channel=NotificationChannel.EMAIL,
                subject=subject,
                message=text_body,
                reference_type=context.get('reference_type', '') if context else '',
                reference_id=context.get('reference_id', '') if context else '',
                metadata=context or {}
            )
            
            # Send email
            success = self.send_email(
                to_email=recipient_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                attachments=attachments,
                notification=notification
            )
            
            if success:
                notification.mark_as_sent()
                logger.info(f"Email sent successfully to {recipient_email}")
            else:
                notification.delivery_status = 'failed'
                notification.save()
                logger.error(f"Failed to send email to {recipient_email}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending notification email: {str(e)}")
            return False
    
    def send_email(
        self, 
        to_email: str, 
        subject: str, 
        text_body: str = "", 
        html_body: str = "",
        attachments: List[str] = None,
        notification: Notification = None
    ) -> bool:
        """
        Send email using Django's email backend or custom SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            text_body: Plain text email body
            html_body: HTML email body
            attachments: List of file paths to attach
            notification: Associated notification object
        
        Returns:
            bool: True if email was sent successfully
        """
        email_log = EmailLog.objects.create(
            notification=notification,
            to_email=to_email,
            from_email=self.from_email,
            subject=subject,
            body_text=text_body,
            body_html=html_body
        )
        
        try:
            if html_body and text_body:
                # Send multipart email (text + HTML)
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_body,
                    from_email=self.from_email,
                    to=[to_email]
                )
                msg.attach_alternative(html_body, "text/html")
                
                # Add attachments if provided
                if attachments:
                    for file_path in attachments:
                        if os.path.exists(file_path):
                            msg.attach_file(file_path)
                
                msg.send()
                
            else:
                # Send simple email
                send_mail(
                    subject=subject,
                    message=text_body or strip_tags(html_body),
                    from_email=self.from_email,
                    recipient_list=[to_email],
                    html_message=html_body if html_body else None,
                    fail_silently=False
                )
            
            # Update email log
            email_log.is_sent = True
            email_log.sent_at = timezone.now()
            email_log.delivery_status = 'sent'
            email_log.save()
            
            return True
            
        except Exception as e:
            # Log error
            email_log.delivery_status = 'failed'
            email_log.error_message = str(e)
            email_log.save()
            
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_bulk_emails(
        self, 
        recipients: List[User], 
        notification_type: str, 
        context: Dict[str, Any] = None
    ) -> Dict[str, int]:
        """
        Send bulk emails to multiple recipients
        
        Args:
            recipients: List of User objects
            notification_type: Type of notification
            context: Email context
        
        Returns:
            Dict with counts of successful and failed sends
        """
        results = {'successful': 0, 'failed': 0}
        
        for user in recipients:
            success = self.send_notification_email(user, notification_type, context)
            if success:
                results['successful'] += 1
            else:
                results['failed'] += 1
        
        return results
    
    def get_user_preferences(self, user: User) -> NotificationPreference:
        """Get or create user notification preferences"""
        preferences, created = NotificationPreference.objects.get_or_create(
            user=user,
            defaults={
                'email_enabled': True,
                'preferred_email': user.email
            }
        )
        return preferences
    
    def get_notification_template(self, notification_type: str) -> Optional[NotificationTemplate]:
        """Get notification template by type"""
        try:
            return NotificationTemplate.objects.get(
                notification_type=notification_type,
                is_active=True
            )
        except NotificationTemplate.DoesNotExist:
            return None
    
    def prepare_email_context(self, user: User, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context for email template rendering"""
        base_context = {
            'user': user,
            'user_name': user.get_full_name() or user.username,
            'site_name': getattr(settings, 'SITE_NAME', 'Scholarship Portal'),
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@scholarshipportal.com'),
            'current_year': timezone.now().year,
        }
        base_context.update(context)
        return base_context
    
    def render_template_string(self, template_string: str, context: Dict[str, Any]) -> str:
        """Render template string with context"""
        if not template_string:
            return ""
        
        try:
            from django.template import Template, Context
            template = Template(template_string)
            return template.render(Context(context))
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            return template_string
    
    def get_user_email(self, user: User, preferences: NotificationPreference) -> str:
        """Get user's preferred email address"""
        return preferences.preferred_email or user.email


class NotificationService:
    """Main service for handling all types of notifications"""
    
    def __init__(self):
        self.email_service = EmailService()
    
    def send_application_submitted_notification(self, application, user: User):
        """Send notification when application is submitted"""
        context = {
            'application': application,
            'application_id': application.id,
            'application_type': getattr(application, 'scholarship_type', 'Scholarship'),
            'reference_type': 'application',
            'reference_id': str(application.id),
        }
        
        return self.email_service.send_notification_email(
            user=user,
            notification_type=NotificationType.APPLICATION_SUBMITTED,
            context=context
        )
    
    def send_application_under_review_notification(self, application, user: User):
        """Send notification when application is under review"""
        context = {
            'application': application,
            'application_id': application.id,
            'application_type': getattr(application, 'scholarship_type', 'Scholarship'),
            'reference_type': 'application',
            'reference_id': str(application.id),
        }
        
        return self.email_service.send_notification_email(
            user=user,
            notification_type=NotificationType.APPLICATION_UNDER_REVIEW,
            context=context
        )
    
    def send_application_approved_notification(self, application, user: User):
        """Send notification when application is approved"""
        context = {
            'application': application,
            'application_id': application.id,
            'application_type': getattr(application, 'scholarship_type', 'Scholarship'),
            'approved_amount': getattr(application, 'approved_amount', 0),
            'reference_type': 'application',
            'reference_id': str(application.id),
        }
        
        return self.email_service.send_notification_email(
            user=user,
            notification_type=NotificationType.APPLICATION_APPROVED,
            context=context
        )
    
    def send_application_rejected_notification(self, application, user: User, reason: str = ""):
        """Send notification when application is rejected"""
        context = {
            'application': application,
            'application_id': application.id,
            'application_type': getattr(application, 'scholarship_type', 'Scholarship'),
            'rejection_reason': reason,
            'reference_type': 'application',
            'reference_id': str(application.id),
        }
        
        return self.email_service.send_notification_email(
            user=user,
            notification_type=NotificationType.APPLICATION_REJECTED,
            context=context
        )
    
    def send_payment_processed_notification(self, payment, user: User):
        """Send notification when payment is processed"""
        context = {
            'payment': payment,
            'payment_amount': payment.amount,
            'payment_method': getattr(payment, 'payment_method', 'Bank Transfer'),
            'reference_type': 'payment',
            'reference_id': str(payment.id),
        }
        
        return self.email_service.send_notification_email(
            user=user,
            notification_type=NotificationType.PAYMENT_PROCESSED,
            context=context
        )
    
    def send_grievance_created_notification(self, grievance, user: User):
        """Send notification when grievance is created"""
        context = {
            'grievance': grievance,
            'grievance_id': grievance.id,
            'grievance_type': grievance.grievance_type,
            'reference_type': 'grievance',
            'reference_id': str(grievance.id),
        }
        
        return self.email_service.send_notification_email(
            user=user,
            notification_type=NotificationType.GRIEVANCE_CREATED,
            context=context
        )
    
    def send_grievance_updated_notification(self, grievance, user: User):
        """Send notification when grievance is updated"""
        context = {
            'grievance': grievance,
            'grievance_id': grievance.id,
            'grievance_status': grievance.status,
            'reference_type': 'grievance',
            'reference_id': str(grievance.id),
        }
        
        return self.email_service.send_notification_email(
            user=user,
            notification_type=NotificationType.GRIEVANCE_UPDATED,
            context=context
        )
    
    def send_bulk_notification(
        self, 
        users: List[User], 
        notification_type: str, 
        context: Dict[str, Any] = None
    ):
        """Send bulk notifications to multiple users"""
        return self.email_service.send_bulk_emails(users, notification_type, context)
    
    def create_in_app_notification(
        self, 
        user: User, 
        notification_type: str, 
        title: str, 
        message: str,
        reference_type: str = "",
        reference_id: str = "",
        metadata: Dict[str, Any] = None
    ) -> Notification:
        """Create in-app notification"""
        return Notification.objects.create(
            recipient=user,
            notification_type=notification_type,
            channel=NotificationChannel.IN_APP,
            subject=title,
            message=message,
            reference_type=reference_type,
            reference_id=reference_id,
            metadata=metadata or {},
            is_sent=True,
            sent_at=timezone.now()
        )
