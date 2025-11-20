from django.core.files.storage import default_storage
from django.conf import settings
import os


class LocalStorage:
    """Local storage backend for file uploads."""
    
    def __init__(self, location=None):
        if location is None:
            location = settings.MEDIA_ROOT
        self.location = location
    
    def save(self, name, content):
        """Save file to local storage."""
        path = os.path.join(self.location, name)
        default_storage.save(path, content)
        return path
    
    def delete(self, name):
        """Delete file from local storage."""
        path = os.path.join(self.location, name)
        if default_storage.exists(path):
            default_storage.delete(path)
    
    def exists(self, name):
        """Check if file exists in local storage."""
        path = os.path.join(self.location, name)
        return default_storage.exists(path)
    
    def url(self, name):
        """Get URL for file in local storage."""
        path = os.path.join(self.location, name)
        return default_storage.url(path)


class S3Storage:
    """S3 storage backend for file uploads."""
    
    def __init__(self, bucket_name=None, location=None):
        from storages.backends.s3boto3 import S3Boto3Storage
        
        if bucket_name is None:
            bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        
        self.storage = S3Boto3Storage(bucket_name=bucket_name)
    
    def save(self, name, content):
        """Save file to S3 storage."""
        return self.storage.save(name, content)
    
    def delete(self, name):
        """Delete file from S3 storage."""
        self.storage.delete(name)
    
    def exists(self, name):
        """Check if file exists in S3 storage."""
        return self.storage.exists(name)
    
    def url(self, name):
        """Get URL for file in S3 storage."""
        return self.storage.url(name)


def get_storage_backend():
    """Get the appropriate storage backend based on settings."""
    if settings.DEFAULT_FILE_STORAGE == 'storages.backends.s3boto3.S3Boto3Storage':
        return S3Storage()
    else:
        return LocalStorage()