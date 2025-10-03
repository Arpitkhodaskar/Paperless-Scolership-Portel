"""
Custom storage backends for AWS S3 integration
"""

from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class StaticStorage(S3Boto3Storage):
    """Storage for static files"""
    location = 'static'
    default_acl = 'public-read'
    file_overwrite = True
    
    def __init__(self, *args, **kwargs):
        kwargs['custom_domain'] = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)
        super().__init__(*args, **kwargs)


class PublicMediaStorage(S3Boto3Storage):
    """Storage for public media files (user uploads that can be public)"""
    location = 'media/public'
    default_acl = 'public-read'
    file_overwrite = False
    
    def __init__(self, *args, **kwargs):
        kwargs['custom_domain'] = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)
        super().__init__(*args, **kwargs)


class PrivateMediaStorage(S3Boto3Storage):
    """Storage for private media files (sensitive documents)"""
    location = 'media/private'
    default_acl = 'private'
    file_overwrite = False
    custom_domain = False  # Force use of S3 domain for signed URLs
    querystring_auth = True  # Enable signed URLs
    
    def __init__(self, *args, **kwargs):
        # Always use S3 domain for private files
        kwargs['custom_domain'] = False
        super().__init__(*args, **kwargs)


class DocumentStorage(S3Boto3Storage):
    """Storage specifically for student documents and applications"""
    location = 'documents'
    default_acl = 'private'
    file_overwrite = False
    custom_domain = False
    querystring_auth = True
    
    def __init__(self, *args, **kwargs):
        kwargs['custom_domain'] = False
        super().__init__(*args, **kwargs)
    
    def get_available_name(self, name, max_length=None):
        """
        Return a filename that's available in the storage.
        Append timestamp to avoid conflicts.
        """
        import os
        from django.utils import timezone
        
        # Get file extension
        name_root, name_ext = os.path.splitext(name)
        
        # Add timestamp to filename
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        name = f"{name_root}_{timestamp}{name_ext}"
        
        return super().get_available_name(name, max_length)


class BackupStorage(S3Boto3Storage):
    """Storage for backup files"""
    bucket_name = getattr(settings, 'BACKUP_S3_BUCKET', 'scholarship-portal-backups')
    location = 'backups'
    default_acl = 'private'
    file_overwrite = False
    custom_domain = False
    
    def __init__(self, *args, **kwargs):
        kwargs['bucket_name'] = self.bucket_name
        kwargs['custom_domain'] = False
        super().__init__(*args, **kwargs)
