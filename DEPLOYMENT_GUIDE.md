# 🚀 Django Scholarship Portal - Production Deployment Guide

This comprehensive guide covers deploying the Django Scholarship Portal to production environments with security best practices, scalability, and reliability.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [AWS Deployment](#aws-deployment)
4. [Heroku Deployment](#heroku-deployment)
5. [DigitalOcean Deployment](#digitalocean-deployment)
6. [Database Setup (AWS RDS)](#database-setup-aws-rds)
7. [File Storage Configuration](#file-storage-configuration)
8. [SSL/HTTPS Setup](#sslhttps-setup)
9. [JWT Authentication Configuration](#jwt-authentication-configuration)
10. [Cron Jobs & Background Tasks](#cron-jobs--background-tasks)
11. [Backup Strategy](#backup-strategy)
12. [Monitoring & Logging](#monitoring--logging)
13. [Performance Optimization](#performance-optimization)

## 🔧 Prerequisites

Before deploying, ensure you have:

- Python 3.9+
- Git repository access
- Domain name (optional but recommended)
- SSL certificates or Let's Encrypt setup
- Environment-specific configuration files

### Required Services:
- **Database**: AWS RDS MySQL or PostgreSQL
- **File Storage**: AWS S3 or DigitalOcean Spaces
- **Email Service**: AWS SES, SendGrid, or Mailgun
- **Monitoring**: Sentry, New Relic, or DataDog

## 🌍 Environment Configuration

### 1. Create Production Settings

Create `scholarship_portal/settings/production.py`:

```python
from .base import *
import os
from decouple import config
import dj_database_url

# Security Settings
DEBUG = False
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# Database Configuration
DATABASES = {
    'default': dj_database_url.parse(config('DATABASE_URL'))
}

# Static Files & Media Storage
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# AWS S3 Configuration for Static & Media Files
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

# Static files storage
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Media files
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# Security Headers
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Session Security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/django.log',
            'maxBytes': 1024*1024*10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'scholarship_portal': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Sentry Configuration (for error tracking)
if config('SENTRY_DSN', default=''):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    
    sentry_sdk.init(
        dsn=config('SENTRY_DSN'),
        integrations=[
            DjangoIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=0.1,
        send_default_pii=True
    )

# Cache Configuration (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Session storage
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# JWT Configuration
SIMPLE_JWT.update({
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'SIGNING_KEY': config('JWT_SIGNING_KEY', default=SECRET_KEY),
})
```

### 2. Environment Variables (.env)

Create `.env` file for production:

```bash
# Security
SECRET_KEY=your-super-secret-key-here-make-it-long-and-complex
JWT_SIGNING_KEY=your-jwt-signing-key-different-from-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,api.yourdomain.com

# Database
DATABASE_URL=mysql://username:password@your-rds-endpoint:3306/scholarship_portal

# AWS Configuration
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_STORAGE_BUCKET_NAME=your-s3-bucket-name
AWS_S3_REGION_NAME=us-east-1

# Email Configuration
EMAIL_HOST=smtp.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-ses-username
EMAIL_HOST_PASSWORD=your-ses-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Redis Cache
REDIS_URL=redis://your-redis-endpoint:6379/1

# Monitoring
SENTRY_DSN=https://your-sentry-dsn-here

# File Upload Limits
FILE_UPLOAD_MAX_MEMORY_SIZE=10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE=10485760  # 10MB
```

## ☁️ AWS Deployment

### 1. EC2 Instance Setup

```bash
# Launch EC2 Instance (Ubuntu 20.04 LTS)
# Instance type: t3.medium or larger for production

# Connect to instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv nginx mysql-client redis-server git

# Install supervisor for process management
sudo apt install -y supervisor

# Create application user
sudo adduser --system --group --home /opt/scholarship_portal scholarship
```

### 2. Application Setup

```bash
# Switch to application user
sudo su - scholarship

# Clone repository
git clone https://github.com/yourusername/scholarship-portal.git /opt/scholarship_portal/app
cd /opt/scholarship_portal/app

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Install additional production packages
pip install gunicorn django-redis boto3 psycopg2-binary

# Create environment file
cp .env.example .env
# Edit .env with production values

# Collect static files
python manage.py collectstatic --noinput --settings=scholarship_portal.settings.production

# Run migrations
python manage.py migrate --settings=scholarship_portal.settings.production

# Create superuser
python manage.py createsuperuser --settings=scholarship_portal.settings.production
```

### 3. Gunicorn Configuration

Create `/opt/scholarship_portal/gunicorn.conf.py`:

```python
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
reload = False

# Logging
accesslog = "/var/log/scholarship_portal/gunicorn_access.log"
errorlog = "/var/log/scholarship_portal/gunicorn_error.log"
loglevel = "info"

# Process naming
proc_name = "scholarship_portal"

# Worker tmp directory
worker_tmp_dir = "/dev/shm"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
```

### 4. Supervisor Configuration

Create `/etc/supervisor/conf.d/scholarship_portal.conf`:

```ini
[program:scholarship_portal]
command=/opt/scholarship_portal/app/venv/bin/gunicorn scholarship_portal.wsgi:application -c /opt/scholarship_portal/gunicorn.conf.py
directory=/opt/scholarship_portal/app
user=scholarship
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/scholarship_portal/gunicorn_supervisor.log
environment=DJANGO_SETTINGS_MODULE="scholarship_portal.settings.production"

[program:scholarship_portal_celery]
command=/opt/scholarship_portal/app/venv/bin/celery -A scholarship_portal worker -l info
directory=/opt/scholarship_portal/app
user=scholarship
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/scholarship_portal/celery.log
environment=DJANGO_SETTINGS_MODULE="scholarship_portal.settings.production"

[program:scholarship_portal_beat]
command=/opt/scholarship_portal/app/venv/bin/celery -A scholarship_portal beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
directory=/opt/scholarship_portal/app
user=scholarship
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/scholarship_portal/celery_beat.log
environment=DJANGO_SETTINGS_MODULE="scholarship_portal.settings.production"
```

### 5. Nginx Configuration

Create `/etc/nginx/sites-available/scholarship_portal`:

```nginx
upstream scholarship_portal {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_stapling on;
    ssl_stapling_verify on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Basic Settings
    client_max_body_size 50M;
    client_body_timeout 120s;
    client_header_timeout 120s;

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types
        application/javascript
        application/json
        application/xml
        text/css
        text/javascript
        text/plain
        text/xml;

    # Static files
    location /static/ {
        alias /opt/scholarship_portal/app/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files (if not using S3)
    location /media/ {
        alias /opt/scholarship_portal/app/media/;
        expires 1y;
        add_header Cache-Control "public";
    }

    # Main application
    location / {
        proxy_pass http://scholarship_portal;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check
    location /health/ {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/scholarship_portal /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 🚀 Heroku Deployment

### 1. Heroku Setup

```bash
# Install Heroku CLI
# Create Heroku app
heroku create scholarship-portal-app

# Add buildpacks
heroku buildpacks:add heroku/python

# Set environment variables
heroku config:set DJANGO_SETTINGS_MODULE=scholarship_portal.settings.production
heroku config:set SECRET_KEY=your-secret-key
heroku config:set DEBUG=False
heroku config:set ALLOWED_HOSTS=scholarship-portal-app.herokuapp.com

# Database addon
heroku addons:create jawsdb:kitefin  # MySQL
# or
heroku addons:create heroku-postgresql:hobby-dev  # PostgreSQL

# Redis addon
heroku addons:create heroku-redis:hobby-dev

# Configure database URL
heroku config:get JAWSDB_URL  # for MySQL
heroku config:set DATABASE_URL=mysql://...
```

### 2. Create Procfile

```procfile
web: gunicorn scholarship_portal.wsgi:application --bind 0.0.0.0:$PORT
worker: celery -A scholarship_portal worker -l info
beat: celery -A scholarship_portal beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### 3. Create runtime.txt

```
python-3.11.0
```

### 4. Deploy

```bash
# Add files to git
git add .
git commit -m "Production deployment configuration"

# Deploy to Heroku
git push heroku main

# Run migrations
heroku run python manage.py migrate

# Create superuser
heroku run python manage.py createsuperuser

# Collect static files
heroku run python manage.py collectstatic --noinput
```

## 🌊 DigitalOcean Deployment

### 1. Droplet Setup

```bash
# Create Droplet (Ubuntu 20.04, 2GB RAM minimum)
# Connect via SSH

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv nginx mysql-client redis-server git supervisor certbot python3-certbot-nginx

# Install Docker (optional for containerized deployment)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### 2. Database Setup (DigitalOcean Managed Database)

```bash
# Create managed MySQL database in DigitalOcean console
# Configure database connection string
# Database URL format: mysql://username:password@hostname:port/database_name
```

### 3. App Platform Deployment (Alternative)

Create `app.yaml`:

```yaml
name: scholarship-portal
services:
- name: web
  source_dir: /
  github:
    repo: yourusername/scholarship-portal
    branch: main
  run_command: gunicorn scholarship_portal.wsgi:application --bind 0.0.0.0:8080
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  routes:
  - path: /
  envs:
  - key: DJANGO_SETTINGS_MODULE
    value: scholarship_portal.settings.production
  - key: SECRET_KEY
    value: your-secret-key
    type: SECRET
  - key: DEBUG
    value: "False"
  - key: DATABASE_URL
    value: your-database-url
    type: SECRET

- name: worker
  source_dir: /
  github:
    repo: yourusername/scholarship-portal
    branch: main
  run_command: celery -A scholarship_portal worker -l info
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: DJANGO_SETTINGS_MODULE
    value: scholarship_portal.settings.production

databases:
- name: scholarship-db
  engine: MYSQL
  version: "8"
  size: db-s-1vcpu-1gb
```

## 🗄️ Database Setup (AWS RDS)

### 1. Create RDS Instance

```bash
# Using AWS CLI
aws rds create-db-instance \
    --db-instance-identifier scholarship-portal-db \
    --db-instance-class db.t3.micro \
    --engine mysql \
    --engine-version 8.0.28 \
    --master-username admin \
    --master-user-password YourSecurePassword123! \
    --allocated-storage 20 \
    --storage-type gp2 \
    --vpc-security-group-ids sg-xxxxxxxxx \
    --db-subnet-group-name default \
    --backup-retention-period 7 \
    --storage-encrypted \
    --multi-az \
    --publicly-accessible \
    --auto-minor-version-upgrade
```

### 2. Security Group Configuration

```bash
# Allow MySQL access from EC2 instances
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxxx \
    --protocol tcp \
    --port 3306 \
    --source-group sg-yyyyyyyyy
```

### 3. Database Connection

```python
# In production.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'scholarship_portal',
        'USER': 'admin',
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': 'scholarship-portal-db.xxxxxxxxx.us-east-1.rds.amazonaws.com',
        'PORT': '3306',
        'OPTIONS': {
            'sql_mode': 'traditional',
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        }
    }
}
```

## 💾 File Storage Configuration

### 1. AWS S3 Setup

```python
# Install boto3
pip install boto3 django-storages

# Settings for S3
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME')
AWS_DEFAULT_ACL = None
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

# Static files
STATICFILES_STORAGE = 'storages.backends.s3boto3.StaticS3Boto3Storage'
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'

# Media files
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.MediaS3Boto3Storage'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
```

### 2. Custom Storage Classes

Create `scholarship_portal/storage_backends.py`:

```python
from storages.backends.s3boto3 import S3Boto3Storage

class StaticStorage(S3Boto3Storage):
    location = 'static'
    default_acl = 'public-read'

class PublicMediaStorage(S3Boto3Storage):
    location = 'media'
    default_acl = 'public-read'
    file_overwrite = False

class PrivateMediaStorage(S3Boto3Storage):
    location = 'private'
    default_acl = 'private'
    file_overwrite = False
    custom_domain = False
```

### 3. S3 Bucket Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::your-bucket-name/static/*"
        },
        {
            "Sid": "AllowApplicationAccess",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR-ACCOUNT-ID:user/your-app-user"
            },
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::your-bucket-name/*"
        }
    ]
}
```

## 🔒 SSL/HTTPS Setup

### 1. Let's Encrypt (Free SSL)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test automatic renewal
sudo certbot renew --dry-run

# Setup auto-renewal cron job
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. AWS Certificate Manager (ACM)

```bash
# Request certificate using AWS CLI
aws acm request-certificate \
    --domain-name yourdomain.com \
    --subject-alternative-names www.yourdomain.com \
    --validation-method DNS \
    --region us-east-1
```

### 3. Cloudflare SSL (Alternative)

```bash
# If using Cloudflare, enable:
# - Full (strict) SSL/TLS encryption mode
# - Always Use HTTPS
# - HTTP Strict Transport Security (HSTS)
# - Minimum TLS Version 1.2
```

## 🔑 JWT Authentication Configuration

### 1. Enhanced JWT Settings

```python
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': config('JWT_SIGNING_KEY'),
    'VERIFYING_KEY': None,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# Rate limiting for auth endpoints
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle'
]

REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '100/hour',
    'user': '1000/hour',
    'login': '5/min',
}
```

### 2. Custom JWT Views

```python
# authentication/views.py
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import UserRateThrottle
from rest_framework.decorators import throttle_classes

class LoginThrottle(UserRateThrottle):
    rate = '5/min'

@throttle_classes([LoginThrottle])
class CustomTokenObtainPairView(TokenObtainPairView):
    pass
```

## ⏰ Cron Jobs & Background Tasks

### 1. Celery Configuration

Create `scholarship_portal/celery.py`:

```python
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scholarship_portal.settings.production')

app = Celery('scholarship_portal')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    'send-notification-emails': {
        'task': 'notifications.tasks.send_pending_notifications',
        'schedule': 60.0,  # Every minute
    },
    'cleanup-expired-tokens': {
        'task': 'authentication.tasks.cleanup_expired_tokens',
        'schedule': 3600.0,  # Every hour
    },
    'generate-daily-reports': {
        'task': 'reporting.tasks.generate_daily_reports',
        'schedule': 86400.0,  # Daily
    },
    'backup-database': {
        'task': 'backups.tasks.backup_database',
        'schedule': 86400.0,  # Daily
    },
    'cleanup-old-files': {
        'task': 'files.tasks.cleanup_old_files',
        'schedule': 604800.0,  # Weekly
    },
}

app.conf.timezone = 'UTC'
```

### 2. Notification Tasks

Create `notifications/tasks.py`:

```python
from celery import shared_task
from django.core.mail import send_mass_mail
from .models import Notification, EmailLog
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_pending_notifications():
    """Send pending email notifications"""
    pending_notifications = Notification.objects.filter(
        status='pending',
        email_sent=False
    )[:100]  # Process in batches
    
    emails = []
    for notification in pending_notifications:
        try:
            # Prepare email content
            subject = notification.subject
            message = notification.render_content()
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [notification.recipient.email]
            
            emails.append((subject, message, from_email, recipient_list))
            
            # Log attempt
            EmailLog.objects.create(
                notification=notification,
                recipient=notification.recipient.email,
                subject=subject,
                status='sending'
            )
            
        except Exception as e:
            logger.error(f"Error preparing notification {notification.id}: {e}")
    
    if emails:
        try:
            send_mass_mail(emails, fail_silently=False)
            
            # Mark as sent
            for notification in pending_notifications:
                notification.email_sent = True
                notification.status = 'sent'
                notification.save()
                
            logger.info(f"Sent {len(emails)} notification emails")
            
        except Exception as e:
            logger.error(f"Error sending emails: {e}")
            
            # Mark as failed
            for notification in pending_notifications:
                notification.status = 'failed'
                notification.save()

@shared_task
def send_application_notification(application_id, notification_type):
    """Send notification for specific application"""
    from applications.models import Application
    
    try:
        application = Application.objects.get(id=application_id)
        # Send notification logic here
        logger.info(f"Sent {notification_type} notification for application {application_id}")
    except Application.DoesNotExist:
        logger.error(f"Application {application_id} not found")

@shared_task
def cleanup_old_notifications():
    """Clean up old notifications and logs"""
    from django.utils import timezone
    from datetime import timedelta
    
    # Delete notifications older than 90 days
    cutoff_date = timezone.now() - timedelta(days=90)
    deleted_notifications = Notification.objects.filter(
        created_at__lt=cutoff_date
    ).delete()
    
    # Delete email logs older than 30 days
    email_cutoff = timezone.now() - timedelta(days=30)
    deleted_logs = EmailLog.objects.filter(
        created_at__lt=email_cutoff
    ).delete()
    
    logger.info(f"Cleaned up {deleted_notifications[0]} notifications and {deleted_logs[0]} email logs")
```

### 3. System Monitoring Tasks

Create `monitoring/tasks.py`:

```python
@shared_task
def check_system_health():
    """Monitor system health and send alerts"""
    import psutil
    import subprocess
    
    # Check disk usage
    disk_usage = psutil.disk_usage('/')
    if disk_usage.percent > 80:
        send_alert_email("High disk usage", f"Disk usage: {disk_usage.percent}%")
    
    # Check memory usage
    memory = psutil.virtual_memory()
    if memory.percent > 80:
        send_alert_email("High memory usage", f"Memory usage: {memory.percent}%")
    
    # Check database connectivity
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as e:
        send_alert_email("Database connection error", str(e))

@shared_task
def backup_uploaded_files():
    """Backup uploaded files to secondary storage"""
    import boto3
    from django.conf import settings
    
    s3 = boto3.client('s3')
    source_bucket = settings.AWS_STORAGE_BUCKET_NAME
    backup_bucket = f"{source_bucket}-backup"
    
    # Copy files to backup bucket
    # Implementation depends on your backup strategy
```

## 🔄 Backup Strategy

### 1. Database Backup Script

Create `scripts/backup_db.py`:

```python
#!/usr/bin/env python
import os
import subprocess
import boto3
from datetime import datetime
from django.conf import settings

def backup_database():
    """Create database backup and upload to S3"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"scholarship_portal_backup_{timestamp}.sql"
    
    # Create database dump
    db_config = settings.DATABASES['default']
    dump_command = [
        'mysqldump',
        f"--host={db_config['HOST']}",
        f"--user={db_config['USER']}",
        f"--password={db_config['PASSWORD']}",
        '--single-transaction',
        '--routines',
        '--triggers',
        db_config['NAME']
    ]
    
    with open(backup_filename, 'w') as backup_file:
        subprocess.run(dump_command, stdout=backup_file, check=True)
    
    # Compress backup
    compressed_filename = f"{backup_filename}.gz"
    subprocess.run(['gzip', backup_filename], check=True)
    
    # Upload to S3
    s3_client = boto3.client('s3')
    backup_bucket = 'scholarship-portal-backups'
    s3_key = f"database_backups/{compressed_filename}"
    
    s3_client.upload_file(
        compressed_filename, 
        backup_bucket, 
        s3_key,
        ExtraArgs={'StorageClass': 'STANDARD_IA'}
    )
    
    # Clean up local file
    os.remove(compressed_filename)
    
    print(f"Database backup completed: {s3_key}")

if __name__ == '__main__':
    backup_database()
```

### 2. File Backup Strategy

```python
# backups/tasks.py
@shared_task
def backup_media_files():
    """Backup media files using AWS S3 cross-region replication"""
    import boto3
    
    # Enable versioning on main bucket
    s3_client = boto3.client('s3')
    
    # Configure cross-region replication
    replication_config = {
        'Role': 'arn:aws:iam::ACCOUNT:role/replication-role',
        'Rules': [
            {
                'ID': 'ReplicateEverything',
                'Status': 'Enabled',
                'Priority': 1,
                'Filter': {},
                'Destination': {
                    'Bucket': 'arn:aws:s3:::scholarship-portal-backup',
                    'StorageClass': 'STANDARD_IA'
                }
            }
        ]
    }
    
    s3_client.put_bucket_replication(
        Bucket='scholarship-portal-media',
        ReplicationConfiguration=replication_config
    )

@shared_task
def cleanup_old_backups():
    """Remove old backup files"""
    import boto3
    from datetime import datetime, timedelta
    
    s3_client = boto3.client('s3')
    backup_bucket = 'scholarship-portal-backups'
    
    # List objects older than 90 days
    cutoff_date = datetime.now() - timedelta(days=90)
    
    response = s3_client.list_objects_v2(Bucket=backup_bucket)
    
    for obj in response.get('Contents', []):
        if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
            s3_client.delete_object(
                Bucket=backup_bucket,
                Key=obj['Key']
            )
            logger.info(f"Deleted old backup: {obj['Key']}")
```

### 3. Backup Verification

```python
@shared_task
def verify_backups():
    """Verify backup integrity"""
    import boto3
    import gzip
    import mysql.connector
    
    s3_client = boto3.client('s3')
    backup_bucket = 'scholarship-portal-backups'
    
    # Get latest backup
    response = s3_client.list_objects_v2(
        Bucket=backup_bucket,
        Prefix='database_backups/',
        MaxKeys=1
    )
    
    if response.get('Contents'):
        latest_backup = response['Contents'][0]['Key']
        
        # Download and test restore
        local_backup = '/tmp/test_backup.sql.gz'
        s3_client.download_file(backup_bucket, latest_backup, local_backup)
        
        # Test if backup is valid
        try:
            with gzip.open(local_backup, 'rt') as f:
                first_line = f.readline()
                if 'MySQL dump' in first_line:
                    logger.info("Backup verification successful")
                else:
                    logger.error("Backup verification failed")
        finally:
            os.remove(local_backup)
```

## 📊 Monitoring & Logging

### 1. Application Performance Monitoring

```python
# Install APM tools
pip install sentry-sdk newrelic

# Sentry configuration in settings
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=config('SENTRY_DSN'),
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
    ],
    traces_sample_rate=0.1,
    send_default_pii=True,
    environment=config('ENVIRONMENT', default='production'),
)
```

### 2. Custom Health Check

Create `health/views.py`:

```python
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import redis

def health_check(request):
    """System health check endpoint"""
    status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status['checks']['database'] = 'healthy'
    except Exception as e:
        status['checks']['database'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'
    
    # Cache check
    try:
        cache.set('health_check', 'ok', 30)
        if cache.get('health_check') == 'ok':
            status['checks']['cache'] = 'healthy'
        else:
            status['checks']['cache'] = 'unhealthy'
    except Exception as e:
        status['checks']['cache'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'
    
    # Storage check (S3)
    try:
        import boto3
        s3_client = boto3.client('s3')
        s3_client.head_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
        status['checks']['storage'] = 'healthy'
    except Exception as e:
        status['checks']['storage'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'
    
    return JsonResponse(status)
```

### 3. Performance Metrics

```python
# monitoring/middleware.py
import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('performance')

class PerformanceMonitoringMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.start_time = time.time()
    
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Log slow requests
            if duration > 2.0:  # 2 seconds threshold
                logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {duration:.2f}s"
                )
            
            # Add performance header
            response['X-Response-Time'] = f"{duration:.3f}s"
        
        return response
```

## 🚀 Performance Optimization

### 1. Database Optimization

```python
# Optimized database settings
DATABASES['default']['OPTIONS'].update({
    'init_command': """
        SET sql_mode='STRICT_TRANS_TABLES';
        SET innodb_lock_wait_timeout=20;
        SET max_execution_time=30000;
    """,
    'read_default_file': '/etc/mysql/my.cnf',
})

# Connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 60

# Read replicas (if applicable)
DATABASE_ROUTERS = ['scholarship_portal.routers.DatabaseRouter']
```

### 2. Caching Strategy

```python
# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL'),
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

# Cache middleware
MIDDLEWARE.insert(1, 'django.middleware.cache.UpdateCacheMiddleware')
MIDDLEWARE.append('django.middleware.cache.FetchFromCacheMiddleware')

CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 600  # 10 minutes
CACHE_MIDDLEWARE_KEY_PREFIX = 'sp'
```

### 3. CDN Configuration

```python
# CloudFlare/CloudFront integration
STATICFILES_STORAGE = 'scholarship_portal.storage.CachedS3StaticStorage'

class CachedS3StaticStorage(StaticS3Boto3Storage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_domain = config('CDN_DOMAIN', default=None)
```

## 🔐 Security Checklist

### 1. Production Security Settings

```python
# Security middleware
MIDDLEWARE.insert(0, 'django.middleware.security.SecurityMiddleware')

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# CORS security
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    'https://yourdomain.com',
    'https://www.yourdomain.com',
]

# File upload security
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644
```

### 2. Rate Limiting

```python
# Install django-ratelimit
pip install django-ratelimit

# In views
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='POST')
def login_view(request):
    pass

@ratelimit(key='user', rate='100/h')
def api_view(request):
    pass
```

This comprehensive deployment guide covers all aspects of deploying your Django scholarship portal to production. Choose the platform that best fits your needs and follow the specific instructions for that platform.

Remember to:
- Test thoroughly in a staging environment first
- Set up monitoring and alerting
- Plan for scalability from the beginning
- Implement proper backup and disaster recovery procedures
- Keep security as a top priority throughout the deployment process
