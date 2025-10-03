# Notification System Configuration
# Add these settings to your main Django settings.py file

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Change to your SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'  # Your email
EMAIL_HOST_PASSWORD = 'your-app-password'  # Your app password

# Default email settings
DEFAULT_FROM_EMAIL = 'noreply@scholarshipportal.com'
NOTIFICATION_FROM_EMAIL = 'notifications@scholarshipportal.com'
SUPPORT_EMAIL = 'support@scholarshipportal.com'

# Notification System Settings
NOTIFICATION_SETTINGS = {
    'BATCH_SIZE': 100,  # Number of emails to send in one batch
    'RETRY_ATTEMPTS': 3,  # Number of retry attempts for failed emails
    'RETRY_DELAY': 300,  # Delay in seconds between retries
    'MAX_DAILY_EMAILS': 1000,  # Maximum emails per day per user
    'ENABLE_EMAIL_NOTIFICATIONS': True,
    'ENABLE_SMS_NOTIFICATIONS': False,  # For future SMS integration
    'ENABLE_PUSH_NOTIFICATIONS': False,  # For future push notifications
    
    # Template settings
    'DEFAULT_TEMPLATE_LANGUAGE': 'en',
    'TEMPLATE_CACHE_TIMEOUT': 3600,  # Cache templates for 1 hour
    
    # Email delivery settings
    'ASYNC_EMAIL_DELIVERY': True,  # Use Celery for async email delivery
    'EMAIL_DELIVERY_TIMEOUT': 30,  # Timeout in seconds
    
    # Logging settings
    'LOG_EMAIL_ATTEMPTS': True,
    'LOG_EMAIL_CONTENT': False,  # Set to True for debugging
    'CLEANUP_LOGS_AFTER_DAYS': 90,  # Clean up logs after 90 days
    
    # Rate limiting
    'RATE_LIMIT_ENABLED': True,
    'RATE_LIMIT_PER_MINUTE': 10,  # Max emails per minute per user
    'RATE_LIMIT_PER_HOUR': 100,   # Max emails per hour per user
}

# Grievance System Settings
GRIEVANCE_SETTINGS = {
    'AUTO_ASSIGN_GRIEVANCES': True,
    'DEFAULT_PRIORITY': 'medium',
    'SLA_RESPONSE_TIME_HOURS': 24,  # Default response time
    'SLA_RESOLUTION_TIME_DAYS': 7,   # Default resolution time
    'AUTO_ESCALATE_AFTER_HOURS': 48, # Auto-escalate if no response
    'ENABLE_FILE_ATTACHMENTS': True,
    'MAX_ATTACHMENT_SIZE_MB': 10,
    'ALLOWED_ATTACHMENT_TYPES': [
        'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif'
    ],
    'AUTO_CLOSE_RESOLVED_AFTER_DAYS': 7,  # Auto-close resolved tickets
    'SATISFACTION_SURVEY_ENABLED': True,
    'ANONYMOUS_GRIEVANCES_ALLOWED': False,
}

# Celery Configuration for Async Tasks (Optional)
# Uncomment and configure if you want to use Celery for background tasks

# CELERY_BROKER_URL = 'redis://localhost:6379/0'
# CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TIMEZONE = 'UTC'

# Logging Configuration
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
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/notifications.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
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
    },
}

# Security Settings
SECURE_SSL_REDIRECT = True  # Redirect to HTTPS
SECURE_HSTS_SECONDS = 31536000  # HTTPS Strict Transport Security
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CORS Settings (if using separate frontend)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React development server
    "http://127.0.0.1:3000",
    # Add your production frontend URLs
]

# DRF Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# Add notifications and grievances to INSTALLED_APPS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'django_filters',
    'corsheaders',
    
    # Your apps
    'notifications',
    'grievances',
    # ... other apps
]

# Middleware
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
