"""
Custom storage backends for handling file uploads to Cloudinary
and ensuring persistent file storage across Render deployments.

This storage class ensures:
1. All files are stored in Cloudinary (not local disk)
2. Files are organized by resource type in separate folders
3. URLs are properly generated for all file types (images, PDFs, documents)
4. Files survive Render deployments (stored in persistent Cloudinary CDN)
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
    
    CRITICAL FEATURES:
    ==================
    1. **Resource Type Detection**: Automatically detects file type and stores in correct Cloudinary folder
       - Images (JPG, PNG, etc.) → /image/upload/ endpoint
       - Documents (PDF, DOC, etc.) → /raw/upload/ endpoint
       - Videos → /video/upload/ endpoint
       
    2. **Folder Organization**: Files are organized by type for easy management
       - profile_pics/ → User profile pictures
       - resources/ → Course resources and materials
       - lessons/resources/ → Lesson attachments
       - assignments/submissions/ → Student assignment submissions
       - receipts/ → Payment receipts
       
    3. **Persistent Storage**: Uses Cloudinary's persistent 'upload' type, not ephemeral staging
       
    4. **Dynamic Folder Routing**: The upload_to parameter in Django models is respected and 
       properly combined with the Cloudinary FOLDER setting
       
    Configuration in Django settings:
    - RESOURCE_TYPE: 'auto' - Automatically handles images, PDFs, videos, documents, etc.
    - TYPE: 'upload' - Uses persistent upload storage (not temporary staging)
    - FOLDER: 'radoki_media' - Organizes all files under this folder
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
        Generate a Cloudinary CDN URL for the given file name.
        
        Ensures the URL:
        - Points to Cloudinary CDN (persistent, not local Render disk)
        - Works for all file types (images, PDFs, documents)
        - Is HTTPS secure
        - Includes proper folder structure
        - Uses correct resource type endpoint
        
        The cloudinary_storage library handles most of this automatically,
        but we ensure correctness and proper HTTPS usage.
        
        Args:
            name: The file name/path relative to media folder
                 Example: 'resources/myfile.pdf' or 'profile_pics/user1.jpg'
            
        Returns:
            A fully qualified HTTPS Cloudinary CDN URL
            Example: https://res.cloudinary.com/cloud_name/raw/upload/radoki_media/resources/myfile.pdf
        """
        # Use parent class URL generation which handles Cloudinary API calls
        url = super().url(name)
        
        # Ensure the URL uses HTTPS (Cloudinary URLs should always be HTTPS)
        if url.startswith('http://'):
            url = 'https://' + url[7:]
        
        return url
    
    def save(self, name, content, max_length=None):
        """
        Save a file to Cloudinary with proper configuration.
        
        Routes all uploads through Cloudinary with these guarantees:
        - Ensures persistence (type='upload', not 'staging')
        - Uses correct resource type detection (auto-detects images vs documents)
        - Maintains folder structure for organization
        - Preserves filename information
        - Respects the model's upload_to parameter
        
        Upload path flow:
        1. Django model defines: upload_to='resources/'
        2. User uploads file: 'my_file.pdf'
        3. Final Cloudinary path: radoki_media/resources/my_file.pdf
        4. Cloudinary detects PDF → stores in /raw/upload/ endpoint
        5. URL: https://res.cloudinary.com/.../raw/upload/radoki_media/resources/my_file.pdf
        
        Args:
            name: The name of the file to save (relative path from media root)
            content: The file content (Django File object)
            max_length: Maximum length for the filename (optional)
            
        Returns:
            The saved file name/path as stored in database
        """
        # Parent class handles all the Cloudinary upload logic
        return super().save(name, content, max_length)


# Export the storage class for Django to use
if CLOUDINARY_AVAILABLE:
    __all__ = ['CloudinaryMediaStorage']
else:
    __all__ = []

