from django.core.management.base import BaseCommand
from notifications.models import NotificationType, NotificationTemplate


class Command(BaseCommand):
    help = 'Create default notification templates'

    def handle(self, *args, **options):
        self.stdout.write('Creating default notification templates...')
        
        # Application notification templates
        templates = [
            {
                'name': 'Application Submitted',
                'notification_type': NotificationType.APPLICATION_SUBMITTED,
                'subject': 'Application Submitted Successfully - {{ application_id }}',
                'html_template': 'notifications/email/application_submitted.html',
                'text_template': 'notifications/email/application_submitted.txt',
                'is_active': True,
                'is_default': True,
                'description': 'Sent when a student submits their scholarship application'
            },
            {
                'name': 'Application Status Updated',
                'notification_type': NotificationType.APPLICATION_STATUS_CHANGED,
                'subject': 'Application Status Update - {{ application_id }}',
                'html_template': 'notifications/email/application_status_updated.html',
                'text_template': 'notifications/email/application_status_updated.txt',
                'is_active': True,
                'is_default': True,
                'description': 'Sent when application status changes (approved, rejected, etc.)'
            },
            {
                'name': 'Payment Notification',
                'notification_type': NotificationType.PAYMENT_CONFIRMATION,
                'subject': 'Payment {{ status|title }} - {{ payment_id }}',
                'html_template': 'notifications/email/payment_notification.html',
                'text_template': 'notifications/email/payment_notification.txt',
                'is_active': True,
                'is_default': True,
                'description': 'Sent for payment-related notifications'
            },
            {
                'name': 'Grievance Status Update',
                'notification_type': NotificationType.GRIEVANCE_STATUS_UPDATE,
                'subject': 'Grievance Update - {{ grievance_id }}',
                'html_template': 'notifications/email/grievance_notification.html',
                'text_template': 'notifications/email/grievance_notification.txt',
                'is_active': True,
                'is_default': True,
                'description': 'Sent when grievance status is updated'
            },
            {
                'name': 'Document Verification Required',
                'notification_type': NotificationType.DOCUMENT_VERIFICATION,
                'subject': 'Documents Required for Verification - {{ application_id }}',
                'html_template': 'notifications/email/application_status_updated.html',
                'text_template': 'notifications/email/application_status_updated.txt',
                'is_active': True,
                'is_default': True,
                'description': 'Sent when additional documents are required'
            },
            {
                'name': 'Welcome Email',
                'notification_type': NotificationType.WELCOME,
                'subject': 'Welcome to Scholarship Portal',
                'html_template': 'notifications/email/welcome.html',
                'text_template': 'notifications/email/welcome.txt',
                'is_active': True,
                'is_default': True,
                'description': 'Welcome email for new users'
            },
            {
                'name': 'Password Reset',
                'notification_type': NotificationType.PASSWORD_RESET,
                'subject': 'Password Reset Request',
                'html_template': 'notifications/email/password_reset.html',
                'text_template': 'notifications/email/password_reset.txt',
                'is_active': True,
                'is_default': True,
                'description': 'Password reset email'
            },
            {
                'name': 'Account Verification',
                'notification_type': NotificationType.ACCOUNT_VERIFICATION,
                'subject': 'Verify Your Account',
                'html_template': 'notifications/email/account_verification.html',
                'text_template': 'notifications/email/account_verification.txt',
                'is_active': True,
                'is_default': True,
                'description': 'Account verification email'
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for template_data in templates:
            template, created = NotificationTemplate.objects.get_or_create(
                notification_type=template_data['notification_type'],
                defaults=template_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template_data["name"]}')
                )
            else:
                # Update existing template
                for key, value in template_data.items():
                    setattr(template, key, value)
                template.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated template: {template_data["name"]}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {created_count + updated_count} templates '
                f'({created_count} created, {updated_count} updated)'
            )
        )
