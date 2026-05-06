"""
Template filters and tags for proper storage URL handling.

Storage-agnostic filters that work with any Django storage backend (S3, R2, Local, etc.).
"""
from django import template
import os
import logging

register = template.Library()
logger = logging.getLogger(__name__)


@register.filter
def storage_file_url(file_field):
    """
    Generate the correct URL for any file type from any storage backend.
    
    This filter is storage-agnostic and handles:
    - Images from any storage backend (local, S3, R2, Cloudinary, etc.)
    - PDFs and documents from any storage backend
    - Automatically gets the correct URL from the storage backend's url() method
    
    Falls back gracefully if file doesn't exist or is empty.
    """
    if not file_field or not file_field.name:
        return ''
    
    try:
        # Use the file field's URL method which respects the storage backend
        url = file_field.url
        
        # Ensure HTTPS for secure delivery
        if url and url.startswith('http://'):
            url = 'https://' + url[7:]
        
        return url
        
    except Exception as e:
        logger.warning(f"Could not generate storage URL for {file_field.name}: {str(e)}")
        return ''


# Keep the old name as an alias for backward compatibility in templates
cloudinary_file_url = storage_file_url


@register.filter
def file_exists(file_field):
    """Check if a file exists in storage."""
    if not file_field or not file_field.name:
        return False
    
    try:
        from django.core.files.storage import default_storage
        return default_storage.exists(file_field.name)
    except Exception:
        return False


@register.filter
def file_size_display(file_field):
    """Display file size in human-readable format."""
    if not file_field or not file_field.name:
        return '0 B'
    
    try:
        size = file_field.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'
    except Exception:
        return '? B'
