from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
import logging

from .services import NotificationService
from .models import NotificationPreference

logger = logging.getLogger(__name__)

# Initialize notification service
notification_service = NotificationService()


@receiver(post_save, sender=User)
def create_notification_preferences(sender, instance, created, **kwargs):
    """Create notification preferences for new users"""
    if created:
        NotificationPreference.objects.create(
            user=instance,
            preferred_email=instance.email
        )


# Application related signals
try:
    # Import application models when available
    from students.models import Application
    
    @receiver(post_save, sender=Application)
    def handle_application_notifications(sender, instance, created, **kwargs):
        """Handle notifications for application status changes"""
        try:
            if created:
                # Application submitted
                notification_service.send_application_submitted_notification(
                    application=instance,
                    user=instance.student.user
                )
                logger.info(f"Sent application submitted notification for application {instance.id}")
            
            else:
                # Check if status changed
                if hasattr(instance, '_original_status'):
                    old_status = instance._original_status
                    new_status = instance.status
                    
                    if old_status != new_status:
                        if new_status == 'under_review':
                            notification_service.send_application_under_review_notification(
                                application=instance,
                                user=instance.student.user
                            )
                        elif new_status == 'approved':
                            notification_service.send_application_approved_notification(
                                application=instance,
                                user=instance.student.user
                            )
                        elif new_status == 'rejected':
                            notification_service.send_application_rejected_notification(
                                application=instance,
                                user=instance.student.user,
                                reason=getattr(instance, 'rejection_reason', '')
                            )
                        
                        logger.info(f"Sent status change notification for application {instance.id}: {old_status} -> {new_status}")
        
        except Exception as e:
            logger.error(f"Error sending application notification: {str(e)}")
    
    @receiver(pre_save, sender=Application)
    def store_original_application_status(sender, instance, **kwargs):
        """Store original status before save to detect changes"""
        if instance.pk:
            try:
                original = Application.objects.get(pk=instance.pk)
                instance._original_status = original.status
            except Application.DoesNotExist:
                instance._original_status = None

except ImportError:
    logger.warning("Application model not found, application notifications disabled")


# Finance/Payment related signals
try:
    from finance.models import Payment
    
    @receiver(post_save, sender=Payment)
    def handle_payment_notifications(sender, instance, created, **kwargs):
        """Handle notifications for payment status changes"""
        try:
            if created and instance.status == 'completed':
                # Payment processed
                notification_service.send_payment_processed_notification(
                    payment=instance,
                    user=instance.application.student.user
                )
                logger.info(f"Sent payment processed notification for payment {instance.id}")
        
        except Exception as e:
            logger.error(f"Error sending payment notification: {str(e)}")

except ImportError:
    logger.warning("Payment model not found, payment notifications disabled")


# Grievance related signals
try:
    from grievances.models import Grievance
    
    @receiver(post_save, sender=Grievance)
    def handle_grievance_notifications(sender, instance, created, **kwargs):
        """Handle notifications for grievance status changes"""
        try:
            if created:
                # New grievance created
                notification_service.send_grievance_created_notification(
                    grievance=instance,
                    user=instance.user
                )
                logger.info(f"Sent grievance created notification for grievance {instance.id}")
            
            else:
                # Check if status changed
                if hasattr(instance, '_original_status'):
                    old_status = instance._original_status
                    new_status = instance.status
                    
                    if old_status != new_status:
                        notification_service.send_grievance_updated_notification(
                            grievance=instance,
                            user=instance.user
                        )
                        logger.info(f"Sent grievance updated notification for grievance {instance.id}: {old_status} -> {new_status}")
        
        except Exception as e:
            logger.error(f"Error sending grievance notification: {str(e)}")
    
    @receiver(pre_save, sender=Grievance)
    def store_original_grievance_status(sender, instance, **kwargs):
        """Store original status before save to detect changes"""
        if instance.pk:
            try:
                original = Grievance.objects.get(pk=instance.pk)
                instance._original_status = original.status
            except Grievance.DoesNotExist:
                instance._original_status = None

except ImportError:
    logger.warning("Grievance model not found, grievance notifications disabled")
