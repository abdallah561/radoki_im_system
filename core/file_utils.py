"""
Utility functions for handling file serving from storage backends.

This module is storage-agnostic and prefers returning direct URLs when possible.
For Cloudflare R2, files are served directly from the R2 endpoint rather than through Django.
"""
import os
import logging
import mimetypes
from django.conf import settings
from django.http import HttpResponse, FileNotFoundError
from django.core.files.storage import default_storage
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


def get_file_url(file_field, force_download=False, filename=None):
    """
    Get the public URL for a file.

    If the storage backend supports direct URLs, this returns the direct URL.
    For force-download requests, it appends the standard S3 response parameter so browsers
    can download the file directly from the storage endpoint.
    """
    if not file_field or not file_field.name:
        return None

    try:
        file_url = file_field.url
        if not file_url:
            return None

        if file_url.startswith('http://'):
            file_url = 'https://' + file_url[7:]

        if force_download:
            filename = filename or os.path.basename(file_field.name)
            separator = '&' if '?' in file_url else '?'
            file_url = f'{file_url}{separator}response-content-disposition=attachment;filename="{filename}"'

        return file_url
    except Exception as e:
        logger.warning(f'Could not get URL for file {getattr(file_field, "name", "")}: {str(e)}')
        return None


def serve_file_response(file_field, force_download=False, filename=None):
    """
    Serve a file by redirecting to its storage URL when available.

    If direct storage access is not available, falls back to reading the file and sending
    it through Django.
    """
    if not file_field or not file_field.name:
        raise ValueError('File field is empty or invalid')

    if not default_storage.exists(file_field.name):
        logger.warning(f'File does not exist: {file_field.name}')
        raise FileNotFoundError(f'File not found: {file_field.name}. It may have been deleted or moved from storage.')

    file_url = get_file_url(file_field, force_download=force_download, filename=filename)
    if file_url:
        logger.info(f'Redirecting to storage URL for file: {file_field.name}')
        return redirect(file_url)

    logger.debug(f'Falling back to local content delivery for file: {file_field.name}')

    with file_field.open('rb') as file_obj:
        file_content = file_obj.read()

    if file_content is None:
        raise ValueError(f'Could not read file content from {file_field.name}')

    content_type, _ = mimetypes.guess_type(file_field.name)
    if content_type is None:
        content_type = 'application/octet-stream'

    response = HttpResponse(file_content, content_type=content_type)
    download_name = filename or os.path.basename(file_field.name)
    disposition_type = 'attachment' if force_download else 'inline'
    response['Content-Disposition'] = f'{disposition_type}; filename="{download_name}"'
    response['Content-Length'] = len(file_content)

    if not force_download:
        response['Cache-Control'] = 'public, max-age=2592000, immutable'

    return response


def file_exists(file_field):
    """
    Check if a file exists in storage.
    """
    if not file_field or not file_field.name:
        return False

    try:
        return default_storage.exists(file_field.name)
    except Exception as e:
        logger.warning(f'Could not check if file exists {getattr(file_field, "name", "")}: {str(e)}')
        return False
