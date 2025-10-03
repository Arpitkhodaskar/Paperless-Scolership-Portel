"""
Celery configuration for scholarship_portal project
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scholarship_portal.settings.production')

# Create Celery app
app = Celery('scholarship_portal')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule Configuration
app.conf.beat_schedule = {
    # Send pending email notifications every minute
    'send-notification-emails': {
        'task': 'notifications.tasks.send_pending_notifications',
        'schedule': 60.0,
    },
    
    # Send batch emails every 5 minutes
    'send-batch-emails': {
        'task': 'notifications.tasks.send_batch_emails',
        'schedule': 300.0,
    },
    
    # Clean up expired JWT tokens every hour
    'cleanup-expired-tokens': {
        'task': 'authentication.tasks.cleanup_expired_tokens',
        'schedule': 3600.0,
    },
    
    # Clean up old notifications daily at 2 AM
    'cleanup-old-notifications': {
        'task': 'notifications.tasks.cleanup_old_notifications',
        'schedule': 86400.0,
    },
    
    # Generate daily reports at 1 AM
    'generate-daily-reports': {
        'task': 'reporting.tasks.generate_daily_reports',
        'schedule': 86400.0,
    },
    
    # Backup database daily at 3 AM
    'backup-database': {
        'task': 'backups.tasks.backup_database',
        'schedule': 86400.0,
    },
    
    # Check system health every 5 minutes
    'check-system-health': {
        'task': 'monitoring.tasks.check_system_health',
        'schedule': 300.0,
    },
    
    # Clean up temporary files weekly on Sunday at 4 AM
    'cleanup-temp-files': {
        'task': 'files.tasks.cleanup_temp_files',
        'schedule': 604800.0,
    },
    
    # Update application statuses every 30 minutes
    'update-application-statuses': {
        'task': 'applications.tasks.update_application_statuses',
        'schedule': 1800.0,
    },
    
    # Check SLA breaches every hour
    'check-sla-breaches': {
        'task': 'grievances.tasks.check_sla_breaches',
        'schedule': 3600.0,
    },
    
    # Send reminder emails for pending actions daily at 10 AM
    'send-reminder-emails': {
        'task': 'notifications.tasks.send_reminder_emails',
        'schedule': 86400.0,
    },
    
    # Archive old grievances monthly on 1st at 5 AM
    'archive-old-grievances': {
        'task': 'grievances.tasks.archive_old_grievances',
        'schedule': 2629746.0,  # Approximately monthly
    },
}

# Celery Configuration
app.conf.update(
    timezone=settings.TIME_ZONE,
    enable_utc=True,
    
    # Task routing
    task_routes={
        'notifications.tasks.*': {'queue': 'notifications'},
        'reporting.tasks.*': {'queue': 'reports'},
        'backups.tasks.*': {'queue': 'backups'},
        'monitoring.tasks.*': {'queue': 'monitoring'},
    },
    
    # Task priorities
    task_annotations={
        'notifications.tasks.send_urgent_notification': {'priority': 9},
        'notifications.tasks.send_pending_notifications': {'priority': 7},
        'backups.tasks.*': {'priority': 3},
        'reporting.tasks.*': {'priority': 5},
    },
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Task result configuration
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f'Request: {self.request!r}')


# Error handling
@app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def robust_task(self):
    """Template for robust tasks with auto-retry"""
    try:
        # Task implementation
        pass
    except Exception as exc:
        # Log the error
        print(f'Task failed: {exc}')
        raise self.retry(exc=exc)


# Custom task base class
from celery import Task

class CallbackTask(Task):
    """Task with callbacks for success and failure"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        print(f'Task {task_id} succeeded: {retval}')
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        print(f'Task {task_id} failed: {exc}')
        # Send alert email or notification
        
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        print(f'Task {task_id} retrying: {exc}')


# Register custom task base
app.Task = CallbackTask
