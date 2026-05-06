"""
Django settings for radoki project.
"""

import environ
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment variables
env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='change-me-in-production-please')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=False)

# Production security settings
if not DEBUG:
    # Security settings for production
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

ALLOWED_HOSTS = env.list(
    'ALLOWED_HOSTS',
    default=['localhost', '127.0.0.1', 'radoki-im-system.onrender.com']
)

# CSRF trusted origins for development and production
CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=[
        'http://127.0.0.1:8000',
        'http://localhost:8000',
        'https://localhost:8000',
        'https://radoki-im-system.onrender.com',
        'https://*.ngrok-free.dev',
        'https://*.ngrok.app',
    ]
)

# Keep CSRF cookie alive for 1 year (default) and session for 2 weeks (default).
CSRF_COOKIE_AGE = 31449600  # 1 year in seconds
CSRF_FAILURE_VIEW = 'core.views.csrf_failure'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'crispy_forms',
    'crispy_bootstrap5',
    'storages',
    # Local apps
    'accounts',
    'courses',
    'payments',
    'dashboard',
    'core',
    'assignments',
    'notifications',
    'referrals',
    'mathfilters',
    'quizzes',
    'attendance',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'radoki.middleware.AuthenticationMiddleware',
]

ROOT_URLCONF = 'radoki.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': False,
        'OPTIONS': {
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'builtins': [
                'core.templatetags.admin_pagination_tags',
            ],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.unread_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'radoki.wsgi.application'

# Database Configuration
# Production: Use Neon PostgreSQL or other production database
# Development: Use SQLite or local PostgreSQL
if 'DATABASE_URL' in os.environ and os.environ.get('DATABASE_URL'):
    # Production database (Neon, RDS, etc.)
    db_config = env.db('DATABASE_URL')
    if db_config.get('ENGINE') == 'django.db.backends.postgresql':
        db_config.setdefault('OPTIONS', {})
        db_config['OPTIONS'].setdefault('sslmode', env('DATABASE_SSL_MODE', default='require'))
        db_config.setdefault('CONN_MAX_AGE', 600)
    DATABASES = {
        'default': db_config
    }
else:
    # Development fallback - SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Cloudflare R2 Configuration for Media Files
# The application uses Cloudflare R2 exclusively for uploaded media when configured.
CLOUDFLARE_R2_ACCESS_KEY_ID = env('CLOUDFLARE_R2_ACCESS_KEY_ID', default='')
CLOUDFLARE_R2_SECRET_ACCESS_KEY = env('CLOUDFLARE_R2_SECRET_ACCESS_KEY', default='')
CLOUDFLARE_R2_BUCKET_NAME = env('CLOUDFLARE_R2_BUCKET_NAME', default='')
CLOUDFLARE_R2_ACCOUNT_ID = env('CLOUDFLARE_R2_ACCOUNT_ID', default='')
CLOUDFLARE_R2_CUSTOM_DOMAIN = env('CLOUDFLARE_R2_CUSTOM_DOMAIN', default='')

if (
    CLOUDFLARE_R2_ACCESS_KEY_ID and
    CLOUDFLARE_R2_SECRET_ACCESS_KEY and
    CLOUDFLARE_R2_BUCKET_NAME and
    CLOUDFLARE_R2_ACCOUNT_ID
):
    DEFAULT_FILE_STORAGE = 'core.storage.CloudflareR2Storage'
    AWS_ACCESS_KEY_ID = CLOUDFLARE_R2_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY = CLOUDFLARE_R2_SECRET_ACCESS_KEY
    AWS_STORAGE_BUCKET_NAME = CLOUDFLARE_R2_BUCKET_NAME
    AWS_S3_ENDPOINT_URL = env(
        'CLOUDFLARE_R2_ENDPOINT_URL',
        default=f'https://{CLOUDFLARE_R2_ACCOUNT_ID}.r2.cloudflarestorage.com'
    )
    AWS_S3_REGION_NAME = env('CLOUDFLARE_R2_REGION', default='auto')
    AWS_S3_CUSTOM_DOMAIN = CLOUDFLARE_R2_CUSTOM_DOMAIN or f'{AWS_STORAGE_BUCKET_NAME}.{CLOUDFLARE_R2_ACCOUNT_ID}.r2.cloudflarestorage.com'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=31536000, public',
    }
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_QUERYSTRING_AUTH = False
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False

    MEDIA_URL = env('MEDIA_URL', default=f'https://{AWS_S3_CUSTOM_DOMAIN}/')
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
elif DEBUG:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
else:
    raise RuntimeError(
        'Cloudflare R2 storage is required in production. '
        'Set CLOUDFLARE_R2_ACCESS_KEY_ID, CLOUDFLARE_R2_SECRET_ACCESS_KEY, '
        'CLOUDFLARE_R2_BUCKET_NAME and CLOUDFLARE_R2_ACCOUNT_ID.'
    )

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Dar_es_Salaam'
USE_I18N = True
USE_TZ = True

STATIC_URL = env('STATIC_URL', default='/static/')
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Static files storage - WhiteNoise for production
# Use explicit safe defaults so collectstatic succeeds in Render build.
STATICFILES_STORAGE = env(
    'STATICFILES_STORAGE',
    default='whitenoise.storage.CompressedManifestStaticFilesStorage' if not DEBUG else 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
)

LOGIN_REDIRECT_URL = '/redirect-after-login/'

AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = 'accounts:login'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Session Configuration for Auto-Logout
# Set to 10 minutes (600 seconds) - matches the inactivity timeout UI + 60-second warning
SESSION_COOKIE_AGE = 600  # 10 minutes in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Expire session when browser closes
SESSION_SAVE_EVERY_REQUEST = True  # Update session on every request to track inactivity
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript from accessing session cookie

# Email Configuration
# Force console backend for local development (when not in production)
# Check if we're in production by looking for RENDER env var or specific production indicators
IS_PRODUCTION = bool(
    os.environ.get('RENDER') or  # Render deployment
    os.environ.get('PRODUCTION') or  # Explicit production flag
    (os.environ.get('DATABASE_URL') and not os.environ.get('LOCAL_DEV'))  # Has DB URL but not local dev flag
)

if not IS_PRODUCTION:
    # Local development - emails go to console
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'test@localhost'
    print("[EMAIL] Using CONSOLE email backend for local development")
else:
    # Production - use Resend HTTP API (most reliable on Render)
    email_backend = env('EMAIL_BACKEND', default='core.email_backends.ResendEmailBackend')
    
    if email_backend == 'core.email_backends.ResendEmailBackend':
        # Resend HTTP API (recommended for Render - no SMTP timeouts)
        EMAIL_BACKEND = 'core.email_backends.ResendEmailBackend'
        RESEND_API_KEY = env('RESEND_API_KEY', default='')
        DEFAULT_FROM_EMAIL = env('RESEND_FROM_EMAIL', default=env('DEFAULT_FROM_EMAIL', default='noreply@localhost'))
        print(f"[EMAIL] Using Resend HTTP API backend for production (from_email={DEFAULT_FROM_EMAIL})")
    else:
        # Fallback to SMTP if explicitly configured
        EMAIL_BACKEND = email_backend
        EMAIL_HOST = env('SMTP_HOST', default='smtp.resend.com')
        EMAIL_PORT = env('SMTP_PORT', default=587)
        EMAIL_USE_TLS = env.bool('SMTP_USE_TLS', default=True)
        EMAIL_USE_SSL = env.bool('SMTP_USE_SSL', default=False)
        EMAIL_TIMEOUT = env.int('SMTP_TIMEOUT', default=10)
        EMAIL_HOST_USER = env('SMTP_USER', default='resend')
        EMAIL_HOST_PASSWORD = env('SMTP_PASSWORD', default='')
        DEFAULT_FROM_EMAIL = env('SMTP_FROM_EMAIL', default=env('DEFAULT_FROM_EMAIL', default='noreply@localhost'))
        print(f"[EMAIL] Using SMTP email backend for production: host={EMAIL_HOST} port={EMAIL_PORT}")

# Logging configuration for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
