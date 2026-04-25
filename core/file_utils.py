"""
Utility functions for handling file serving from both local and Cloudinary storage.

IMPORTANT: For Cloudinary storage, we redirect to Cloudinary URLs directly instead of
fetching files through the Django server. This avoids 404 errors, improves performance,
and lets browsers cache files directly from the CDN.

For local storage, we still serve files through Django for backwards compatibility.
"""
import os
import logging
import mimetypes
from django.conf import settings
from django.http import FileResponse, HttpResponse, FileNotFoundError
from django.core.files.storage import default_storage
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


def _is_using_cloudinary():
    """Check if the project is configured to use Cloudinary storage."""
    return (
        getattr(settings, 'CLOUDINARY_CLOUD_NAME', '') and
        getattr(settings, 'CLOUDINARY_API_KEY', '') and
        getattr(settings, 'CLOUDINARY_API_SECRET', '')
    )


def get_cloudinary_url(file_field, force_download=False):
    """
    Get the proper Cloudinary URL for a file with correct parameters.
    
    For Cloudinary files, this returns the CDN URL that should be used directly.
    The browser will download/display the file directly from Cloudinary's servers,
    not through Django.
    
    Args:
        file_field: Django FileField instance
        force_download: If True, add ?fl_attachment to force download
    
    Returns:
        The Cloudinary URL string, or None if file is empty
    """
    if not file_field or not file_field.name:
        return None
    
    try:
        file_url = file_field.url
        
        if not file_url:
            logger.warning(f"Could not get URL for file field")
            return None
        
        # Ensure it's HTTPS
        if file_url.startswith('http://'):
            file_url = 'https://' + file_url[7:]
        
        # Get file extension
        _, ext = os.path.splitext(file_field.name)
        ext = ext.lower()
        
        # Add appropriate parameters based on file type and download flag
        if force_download:
            # Add attachment flag for force download
            separator = '?' if '?' not in file_url else '&'
            file_url = f"{file_url}{separator}fl_attachment"
        
        logger.debug(f"Generated Cloudinary URL: {file_url}")
        return file_url
        
    except Exception as e:
        logger.error(f"Error generating Cloudinary URL for {file_field.name}: {str(e)}", exc_info=True)
        return None


def serve_file_response(file_field, force_download=False, filename=None):
    """
    Serve a file from either local storage or Cloudinary.
    
    FOR CLOUDINARY FILES: Returns a redirect response to the Cloudinary URL.
    The browser will download/display directly from Cloudinary's CDN, which is faster
    and more reliable than fetching through Django.
    
    FOR LOCAL FILES: Returns the file content through Django (backwards compatibility).
    
    Args:
        file_field: Django FileField instance
        force_download: If True, file will be downloaded (not displayed inline)
        filename: Optional filename for download (defaults to original filename)
    
    Returns:
        Redirect response (for Cloudinary) or HttpResponse with file content (for local)
    
    Raises:
        Exception: If file cannot be served
    """
    if not file_field or not file_field.name:
        raise ValueError("File field is empty or invalid")
    
    # Check if file exists
    if not file_field.storage.exists(file_field.name):
        logger.warning(f"File does not exist: {file_field.name}")
        raise FileNotFoundError(f"File not found: {file_field.name}. It may have been deleted or moved from storage.")
    
    try:
        file_path = file_field.name
        
        # Check if using Cloudinary storage
        if _is_using_cloudinary():
            # For Cloudinary, get the URL and let the browser fetch it directly
            cloudinary_url = get_cloudinary_url(file_field, force_download=force_download)
            
            if cloudinary_url:
                logger.info(f"Redirecting to Cloudinary URL for file: {file_path}")
                # Return redirect to Cloudinary URL
                # The browser will handle the download/display
                return redirect(cloudinary_url)
            else:
                # If we couldn't generate a URL, fall back to local file reading
                logger.warning(f"Could not generate Cloudinary URL, falling back to local read for: {file_path}")
                # Fall through to local file handling below
        
        # For local storage or as fallback
        logger.debug(f"Using local storage for file: {file_path}")
        
        # Get file content
        with file_field.open('rb') as file_obj:
            file_content = file_obj.read()
        
        if file_content is None:
            raise ValueError(f"Could not read file content from {file_path}")
        
        logger.debug(f"Successfully read {len(file_content)} bytes from {file_path}")
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        logger.debug(f"Content-Type determined as: {content_type}")
        
        # Create response
        response = HttpResponse(file_content, content_type=content_type)
        
        # Set filename
        dl_filename = filename or os.path.basename(file_path)
        if force_download:
            response['Content-Disposition'] = f'attachment; filename="{dl_filename}"'
        else:
            # For inline viewing (like PDF preview), use inline disposition
            response['Content-Disposition'] = f'inline; filename="{dl_filename}"'
        
        response['Content-Length'] = len(file_content)
        
        # Add caching headers for better performance
        if not force_download:  # Don't cache downloads
            response['Cache-Control'] = 'public, max-age=2592000, immutable'  # 30 days
        
        return response
        
    except Exception as e:
        logger.error(f"Error serving file {file_field.name}: {str(e)}", exc_info=True)
        raise


def get_file_url(file_field):
    """
    Get the URL for a file, handling both local and Cloudinary storage.
    
    For local files, returns /media/... path.
    For Cloudinary files, returns the Cloudinary CDN URL.
    
    Args:
        file_field: Django FileField instance
    
    Returns:
        URL string or None if file is empty
    """
    if not file_field or not file_field.name:
        return None
    
    try:
        # Try to get the URL from the storage backend
        url = file_field.url
        
        # Ensure HTTPS for Cloudinary URLs
        if url and url.startswith('http://'):
            url = 'https://' + url[7:]
        
        return url
    except Exception as e:
        logger.warning(f"Could not get URL for file {file_field.name}: {str(e)}")
        # Fallback: construct local media URL
        return f"{settings.MEDIA_URL}{file_field.name}"


def file_exists(file_field):
    """
    Check if a file actually exists (either locally or on Cloudinary).
    
    Args:
        file_field: Django FileField instance
    
    Returns:
        Boolean indicating if file exists
    """
    if not file_field or not file_field.name:
        return False
    
    try:
        # Check if file exists in storage
        return default_storage.exists(file_field.name)
    except Exception as e:
        logger.warning(f"Could not check if file exists {file_field.name}: {str(e)}")
        return False
