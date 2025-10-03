"""
Production settings for scholarship_portal project.
"""

from .base import *
from decouple import config
import dj_database_url
import os

# Security Settings
DEBUG = False
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# JWT Signing Key (different from SECRET_KEY for added security)
SIMPLE_JWT['SIGNING_KEY'] = config('JWT_SIGNING_KEY', default=SECRET_KEY)

# Database Configuration - AWS RDS MySQL
DATABASES = {
    'default': dj_database_url.parse(config('DATABASE_URL'))
}

# Database connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['OPTIONS'] = {
    'sql_mode': 'traditional',
    'charset': 'utf8mb4',
    'init_command': """
        SET sql_mode='STRICT_TRANS_TABLES';
        SET innodb_lock_wait_timeout=20;
        SET max_execution_time=30000;
    """,
}

# AWS S3 Configuration for Static & Media Files
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
AWS_S3_CUSTOM_DOMAIN = config('AWS_S3_CUSTOM_DOMAIN', default=f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com')
AWS_DEFAULT_ACL = None
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = False

# Static files storage
STATICFILES_STORAGE = 'scholarship_portal.storage.StaticStorage'
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'

# Media files storage
DEFAULT_FILE_STORAGE = 'scholarship_portal.storage.PublicMediaStorage'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# Private file storage for sensitive documents
PRIVATE_FILE_STORAGE = 'scholarship_portal.storage.PrivateMediaStorage'

# Security Headers
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

# Session Security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CORS Configuration
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

# Email Configuration - AWS SES
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='email-smtp.us-east-1.amazonaws.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')
SERVER_EMAIL = config('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)

# Cache Configuration - Redis
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
        },
        'KEY_PREFIX': 'scholarship_portal',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Session storage
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Cache middleware
MIDDLEWARE.insert(1, 'django.middleware.cache.UpdateCacheMiddleware')
MIDDLEWARE.append('django.middleware.cache.FetchFromCacheMiddleware')

CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 600  # 10 minutes
CACHE_MIDDLEWARE_KEY_PREFIX = 'sp'

# Celery Configuration for Background Tasks
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default=config('REDIS_URL', default='redis://localhost:6379/0'))
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default=config('REDIS_URL', default='redis://localhost:6379/0'))
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    'send-notification-emails': {
        'task': 'notifications.tasks.send_pending_notifications',
        'schedule': 60.0,  # Every minute
    },
    'cleanup-expired-tokens': {
        'task': 'authentication.tasks.cleanup_expired_tokens',
        'schedule': 3600.0,  # Every hour
    },
    'cleanup-old-notifications': {
        'task': 'notifications.tasks.cleanup_old_notifications',
        'schedule': 86400.0,  # Daily
    },
    'backup-database': {
        'task': 'backups.tasks.backup_database',
        'schedule': 86400.0,  # Daily at midnight
    },
    'generate-daily-reports': {
        'task': 'reporting.tasks.generate_daily_reports',
        'schedule': 86400.0,  # Daily
    },
    'check-system-health': {
        'task': 'monitoring.tasks.check_system_health',
        'schedule': 300.0,  # Every 5 minutes
    },
    'cleanup-old-files': {
        'task': 'files.tasks.cleanup_old_files',
        'schedule': 604800.0,  # Weekly
    },
}

# Sentry Configuration for Error Tracking
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=0.1,
        send_default_pii=True,
        environment='production',
        release=config('APP_VERSION', default='1.0.0'),
    )

# Enhanced Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"level": "{levelname}", "time": "{asctime}", "module": "{module}", "message": "{message}"}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/scholarship_portal/django.log',
            'maxBytes': 1024*1024*10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/scholarship_portal/django_errors.log',
            'maxBytes': 1024*1024*10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'scholarship_portal': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'notifications': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'grievances': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'celery': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'security': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Admin Configuration
ADMINS = [
    ('Admin', config('ADMIN_EMAIL', default='admin@scholarshipportal.com')),
]
MANAGERS = ADMINS

# Performance Monitoring
if config('ENABLE_PERFORMANCE_MONITORING', default=False, cast=bool):
    MIDDLEWARE.insert(0, 'scholarship_portal.middleware.PerformanceMonitoringMiddleware')

# Rate Limiting Enhancement
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].update({
    'login': '5/min',
    'password_reset': '3/hour',
    'contact': '10/hour',
    'upload': '20/hour',
})

# Database Query Optimization
if config('ENABLE_QUERY_LOGGING', default=False, cast=bool):
    LOGGING['loggers']['django.db.backends'] = {
        'handlers': ['file'],
        'level': 'DEBUG',
        'propagate': False,
    }

# Content Security Policy (if django-csp is installed)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
CSP_IMG_SRC = ("'self'", "data:", f"https://{AWS_S3_CUSTOM_DOMAIN}")
CSP_CONNECT_SRC = ("'self'",)

# Backup Configuration
BACKUP_SETTINGS = {
    'DATABASE_BACKUP_ENABLED': config('DATABASE_BACKUP_ENABLED', default=True, cast=bool),
    'MEDIA_BACKUP_ENABLED': config('MEDIA_BACKUP_ENABLED', default=True, cast=bool),
    'BACKUP_RETENTION_DAYS': config('BACKUP_RETENTION_DAYS', default=90, cast=int),
    'BACKUP_S3_BUCKET': config('BACKUP_S3_BUCKET', default='scholarship-portal-backups'),
    'BACKUP_ENCRYPTION_KEY': config('BACKUP_ENCRYPTION_KEY', default=''),
}

# Monitoring URLs and Health Checks
HEALTH_CHECK_SETTINGS = {
    'ENABLE_HEALTH_CHECKS': True,
    'DATABASE_CHECK': True,
    'CACHE_CHECK': True,
    'STORAGE_CHECK': True,
    'CELERY_CHECK': True,
}

# Create log directories
os.makedirs('/var/log/scholarship_portal', exist_ok=True)
