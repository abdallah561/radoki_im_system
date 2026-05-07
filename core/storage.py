"""
Custom storage backend for Cloudflare R2 media storage.

This storage class ensures all Django media uploads are written to Cloudflare R2
and served directly from the R2 endpoint or custom domain.
"""

import logging
from django.conf import settings

try:
    from storages.backends.s3boto3 import S3Boto3Storage
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False


logger = logging.getLogger(__name__)


class CloudflareR2Storage(S3Boto3Storage if STORAGE_AVAILABLE else object):
    """Django storage backend that uploads media files to Cloudflare R2."""

    default_acl = 'public-read'
    file_overwrite = False
    querystring_auth = False
    object_parameters = {'CacheControl': 'max-age=31536000, public'}
    signature_version = 's3v4'
    location = ''  # Don't include bucket name in object path

    def __init__(self, *args, **kwargs):
        if not STORAGE_AVAILABLE:
            raise ImportError(
                'django-storages[boto3] is required for Cloudflare R2 storage. '
                'Install it with: pip install django-storages[boto3]'
            )

        custom_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None) or None
        if custom_domain:
            custom_domain = custom_domain.strip()
            if custom_domain.startswith('http://'):
                custom_domain = custom_domain[len('http://'):]
            elif custom_domain.startswith('https://'):
                custom_domain = custom_domain[len('https://'):]
            custom_domain = custom_domain.rstrip('/')

        self.querystring_auth = getattr(settings, 'AWS_QUERYSTRING_AUTH', self.querystring_auth)

        kwargs.setdefault('bucket_name', getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None))
        kwargs.setdefault('custom_domain', custom_domain)
        kwargs.setdefault('endpoint_url', getattr(settings, 'AWS_S3_ENDPOINT_URL', None))
        kwargs.setdefault('region_name', getattr(settings, 'AWS_S3_REGION_NAME', None))
        super().__init__(*args, **kwargs)

    def _log_storage_error(self, operation, name, exc, extra=None):
        message = f'Cloudflare R2 storage {operation} failed for "{name}".'
        if extra:
            message += f' {extra}'
        logger.error(message, exc_info=True)

    def save(self, name, content, max_length=None):
        try:
            return super().save(name, content, max_length=max_length)
        except Exception as exc:
            self._log_storage_error('save', name, exc, f'max_length={max_length}')
            raise

    def delete(self, name):
        try:
            return super().delete(name)
        except Exception as exc:
            self._log_storage_error('delete', name, exc)
            raise

    def exists(self, name):
        try:
            return super().exists(name)
        except Exception as exc:
            self._log_storage_error('exists', name, exc)
            return False

    def open(self, name, mode='rb'):
        try:
            return super().open(name, mode)
        except Exception as exc:
            self._log_storage_error('open', name, exc, f'mode={mode}')
            raise

    def url(self, name, parameters=None, expire=None, http_method=None):
        try:
            url = super().url(name, parameters=parameters, expire=expire, http_method=http_method)
            if url and url.startswith('http://'):
                url = 'https://' + url[7:]

            if not getattr(settings, 'DEBUG', False):
                logger.debug('Cloudflare R2 URL generated for %s: %s', name, url)

            return url
        except Exception as exc:
            self._log_storage_error('url', name, exc)
            raise


__all__ = ['CloudflareR2Storage']

