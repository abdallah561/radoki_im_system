"""
Custom storage backend for Cloudflare R2 media storage.

This storage class ensures all Django media uploads are written to Cloudflare R2
and served directly from the R2 endpoint or custom domain.
"""

from django.conf import settings

try:
    from storages.backends.s3boto3 import S3Boto3Storage
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False


class CloudflareR2Storage(S3Boto3Storage if STORAGE_AVAILABLE else object):
    """Django storage backend that uploads media files to Cloudflare R2."""

    default_acl = None
    file_overwrite = False
    querystring_auth = False
    object_parameters = {'CacheControl': 'max-age=31536000, public'}
    signature_version = 's3v4'

    def __init__(self, *args, **kwargs):
        if not STORAGE_AVAILABLE:
            raise ImportError(
                'django-storages[boto3] is required for Cloudflare R2 storage. '
                'Install it with: pip install django-storages[boto3]'
            )

        kwargs.setdefault('bucket_name', getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None))
        kwargs.setdefault('custom_domain', getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None))
        kwargs.setdefault('endpoint_url', getattr(settings, 'AWS_S3_ENDPOINT_URL', None))
        super().__init__(*args, **kwargs)

    def url(self, name):
        url = super().url(name)
        if url and url.startswith('http://'):
            url = 'https://' + url[7:]
        return url


__all__ = ['CloudflareR2Storage']

