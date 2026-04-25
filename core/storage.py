"""
Custom storage backends for handling file uploads to Cloudinary
and ensuring persistent file storage across Render deployments.
"""

import os
from django.conf import settings
from urllib.parse import urljoin

try:
    from cloudinary_storage.storage import MediaCloudinaryStorage
    import cloudinary
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False
    MediaCloudinaryStorage = None


class CloudinaryMediaStorage(MediaCloudinaryStorage if CLOUDINARY_AVAILABLE else object):
    """
    Enhanced Cloudinary storage for all media files (images, PDFs, documents, videos, etc.)
    Ensures all file types are properly stored and served from Cloudinary CDN with persistence.
    
    Key Features:
    - Automatically determines resource type for each file (image, video, raw, etc.)
    - Routes all uploads to Cloudinary (no local disk storage)
    - Generates persistent URLs pointing to Cloudinary CDN
    - Works with Render's ephemeral file system
    - Supports all file formats: images, PDFs, Word docs, Excel sheets, etc.
    
    Configuration:
    - RESOURCE_TYPE: 'auto' - Automatically handles images, PDFs, videos, documents, etc.
    - TYPE: 'upload' - Uses persistent upload storage (not temporary staging)
    - FOLDER: 'radoki_media' - Organizes all files under a consistent folder structure
    - SECURE: True - Always uses HTTPS for CDN delivery
    - USE_FILENAME: True - Preserves original filenames when possible
    - UNIQUE_FILENAME: True - Prevents filename collisions
    """
    
    def __init__(self):
        if CLOUDINARY_AVAILABLE:
            super().__init__()
        else:
            raise ImportError("cloudinary_storage is not installed. Install with: pip install cloudinary django-cloudinary-storage")
    
    def url(self, name):
        """
        Generate a Cloudinary URL for the given file name.
        
        Ensures the URL:
        - Points to Cloudinary CDN (persistent, not local)
        - Works for all file types (images, PDFs, documents)
        - Is HTTPS secure
        - Includes proper folder structure
        
        Args:
            name: The file name/path relative to media folder
            
        Returns:
            A fully qualified HTTPS Cloudinary CDN URL
        """
        # Use parent class URL generation which handles Cloudinary specifics
        url = super().url(name)
        
        # Ensure the URL uses HTTPS
        if url.startswith('http://'):
            url = 'https://' + url[7:]
        
        # Ensure URL points to raw/upload endpoint for all file types
        # The parent class should handle this, but this ensures it's correct
        if '/image/upload/' in url and not url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')):
            # Non-image file with image endpoint - this shouldn't happen but handle it
            url = url.replace('/image/upload/', '/raw/upload/')
        
        return url
    
    def save(self, name, content, max_length=None):
        """
        Save a file to Cloudinary.
        
        Routes all uploads through Cloudinary with proper configuration:
        - Ensures persistence (type='upload')
        - Uses correct resource type detection
        - Maintains folder structure
        - Preserves filename information
        
        Args:
            name: The name of the file to save (relative path)
            content: The file content
            max_length: Maximum length for the filename
            
        Returns:
            The saved file name/path
        """
        return super().save(name, content, max_length)


# Export the storage class for Django to use
if CLOUDINARY_AVAILABLE:
    __all__ = ['CloudinaryMediaStorage']
else:
    __all__ = []

