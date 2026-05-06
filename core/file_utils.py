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
        logger.warning('Attempted to get URL for an invalid or empty file field.')
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
    except Exception as exc:
        logger.error(
            f'Could not get URL for file {getattr(file_field, "name", "")} : {str(exc)}',
            exc_info=True,
        )
        return None


def serve_file_response(file_field, force_download=False, filename=None):
    """
    Serve a file by redirecting to its storage URL when available.

    If direct storage access is not available, falls back to reading the file and sending
    it through Django.
    """
    if not file_field or not file_field.name:
        logger.error('Attempted to serve an invalid or empty file field.')
        raise ValueError('File field is empty or invalid')

    try:
        exists = default_storage.exists(file_field.name)
    except Exception as exc:
        logger.error(
            f'Error checking file existence for {file_field.name}: {str(exc)}',
            exc_info=True,
        )
        raise

    if not exists:
        logger.warning(f'File does not exist in storage: {file_field.name}')
        raise FileNotFoundError(
            f'File not found: {file_field.name}. It may have been deleted or moved from storage.'
        )

    file_url = get_file_url(file_field, force_download=force_download, filename=filename)
    if file_url:
        logger.info(f'Redirecting to storage URL for file: {file_field.name}')
        return redirect(file_url)

    logger.warning(
        f'Unable to generate direct storage URL for file {file_field.name}; falling back to server-side delivery.'
    )

    try:
        with file_field.open('rb') as file_obj:
            file_content = file_obj.read()
    except Exception as exc:
        logger.error(
            f'Error reading file content from {file_field.name}: {str(exc)}',
            exc_info=True,
        )
        raise

    if file_content is None:
        logger.error(f'File {file_field.name} returned no content when opened.')
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
        logger.warning('Attempted to check existence for an invalid or empty file field.')
        return False

    try:
        return default_storage.exists(file_field.name)
    except Exception as exc:
        logger.error(
            f'Could not check if file exists {getattr(file_field, "name", "")} : {str(exc)}',
            exc_info=True,
        )
        return False
