

from datetime import timedelta

from pathlib import Path

from decouple import Csv, config
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent



DEBUG = config("DEBUG", default=True, cast=bool)

SECRET_KEY = config("SECRET_KEY", default="")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-secret-key-change-me"
    else:
        raise ValueError("SECRET_KEY environment variable is required when DEBUG=False.")

ALLOWED_HOSTS = [
    *config("ALLOWED_HOSTS", default="localhost,127.0.0.1,testserver", cast=Csv()),
]



INSTALLED_APPS = [
    "django_prometheus",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.gis',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'channels',
    'corsheaders',
    'storages',
    "rest_framework_simplejwt.token_blacklist",
    "drf_yasg",

    'apps.core',
    'apps.authentication',
    'apps.company',
    'apps.company_admin',
    'apps.billing',
    'apps.main_admin',
    'apps.driver',
    'apps.shops',
    'apps.chats',
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middlewares.TenantMiddleware',
    'apps.billing.middlewares.SubscriptionAccessMiddleware',
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = "config.asgi.application"




DATABASES = {
    'default': {
        'ENGINE': config("DB_ENGINE", default="django.contrib.gis.db.backends.postgis"),
        'NAME': config("DB_NAME", default="route_db"),
        'USER': config("DB_USER", default="postgres"),
        'PASSWORD': config("DB_PASSWORD", default=""),
        'HOST': config("DB_HOST", default="localhost"),
        'PORT': config("DB_PORT", default="5432"),
    }
}

if not DEBUG and not DATABASES["default"]["PASSWORD"]:
    raise ValueError("DB_PASSWORD environment variable is required when DEBUG=False.")

GDAL_LIBRARY_PATH = config("GDAL_LIBRARY_PATH", default=None)
GEOS_LIBRARY_PATH = config("GEOS_LIBRARY_PATH", default=None)


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    "EXCEPTION_HANDLER": "apps.core.api_exception_handler.custom_exception_handler",
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'ISSUER': 'route-management',
    'AUDIENCE': 'route-management-users',
}

AUTH_USER_MODEL = 'authentication.User'

SESSION_COOKIE_SAMESITE = config("SESSION_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SAMESITE = config("CSRF_COOKIE_SAMESITE", default="Lax")
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=not DEBUG, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=not DEBUG, cast=bool)

REFRESH_COOKIE_SECURE = config("REFRESH_COOKIE_SECURE", default=SESSION_COOKIE_SECURE, cast=bool)
REFRESH_COOKIE_SAMESITE = config("REFRESH_COOKIE_SAMESITE", default=SESSION_COOKIE_SAMESITE)
_refresh_cookie_domain = config("REFRESH_COOKIE_DOMAIN", default="")
REFRESH_COOKIE_DOMAIN = _refresh_cookie_domain or None

CORS_ALLOWED_ORIGINS = [
    *config("CORS_ALLOWED_ORIGINS", default="http://localhost:5173,http://127.0.0.1:5173", cast=Csv()),
]

CORS_ALLOW_CREDENTIALS = True

if not DEBUG:
    SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True, cast=bool)
    SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=True, cast=bool)
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


RAZORPAY_KEY_ID = config("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = config("RAZORPAY_KEY_SECRET", default="")

EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER or "noreply.routemaster@gmail.com")


SWAGGER_SETTINGS = {
    "USE_SESSION_AUTH": False,
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
        }
    },
}


PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
]


USE_REDIS_CACHE = config("USE_REDIS_CACHE", default=not DEBUG, cast=bool)
REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/1")
if USE_REDIS_CACHE:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,
                "SOCKET_CONNECT_TIMEOUT": config("REDIS_CONNECT_TIMEOUT", default=0.2, cast=float),
                "SOCKET_TIMEOUT": config("REDIS_SOCKET_TIMEOUT", default=0.2, cast=float),
            },
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "route-management-local-cache",
        }
    }

TENANT_CACHE_TIMEOUT = config("TENANT_CACHE_TIMEOUT", default=300, cast=int)


CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=config("REDIS_URL", default="redis://127.0.0.1:6379/1"))
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", default=False, cast=bool)
SEND_OTP_ASYNC = config("SEND_OTP_ASYNC", default=False, cast=bool)
REGISTRATION_OTP_TTL_SECONDS = config("REGISTRATION_OTP_TTL_SECONDS", default=300, cast=int)
CHAT_PUSH_ENABLED = config("CHAT_PUSH_ENABLED", default=True, cast=bool)
FIREBASE_CREDENTIALS_FILE = config("FIREBASE_CREDENTIALS_FILE", default="")
FIREBASE_PROJECT_ID = config("FIREBASE_PROJECT_ID", default="")
ENFORCE_SUBSCRIPTION_ACCESS = config("ENFORCE_SUBSCRIPTION_ACCESS", default=True, cast=bool)
SUBSCRIPTION_GRACE_DAYS = config("SUBSCRIPTION_GRACE_DAYS", default=0, cast=int)
SUBSCRIPTION_STATE_CACHE_SECONDS = config("SUBSCRIPTION_STATE_CACHE_SECONDS", default=60, cast=int)
SUBSCRIPTION_EXEMPT_PATH_PREFIXES = [
    *config(
        "SUBSCRIPTION_EXEMPT_PATH_PREFIXES",
        default="/admin/,/swagger/,/redoc/,/api/auth/,/api/billing/,/health/,/metrics",
        cast=Csv(),
    ),
]

AI_SERVICE_URL = config("AI_SERVICE_URL", default="http://ai_service:8001")
AI_SERVICE_TIMEOUT_SECONDS = config("AI_SERVICE_TIMEOUT_SECONDS", default=20, cast=int)
AI_SYNC_QUEUE_LOCK_SECONDS = config("AI_SYNC_QUEUE_LOCK_SECONDS", default=300, cast=int)
AI_AUTOSYNC_ENABLED = config("AI_AUTOSYNC_ENABLED", default=True, cast=bool)
AI_AUTOSYNC_INTERVAL_MINUTES = config("AI_AUTOSYNC_INTERVAL_MINUTES", default=15, cast=int)
AI_INTERNAL_AUTH_SECRET = config("AI_INTERNAL_AUTH_SECRET", default=SECRET_KEY)
AI_INTERNAL_AUTH_ISSUER = config("AI_INTERNAL_AUTH_ISSUER", default="core_service")
AI_INTERNAL_AUTH_AUDIENCE = config("AI_INTERNAL_AUTH_AUDIENCE", default="ai_service_internal")
AI_INTERNAL_AUTH_TOKEN_TTL_SECONDS = config("AI_INTERNAL_AUTH_TOKEN_TTL_SECONDS", default=300, cast=int)

MONGO_URI = config("MONGO_URI", default="mongodb://mongo:27017")
MONGO_DB_NAME = config("MONGO_DB_NAME", default="route_tracking")
MONGO_LOCATIONS_COLLECTION = config("MONGO_LOCATIONS_COLLECTION", default="driver_locations")
LIVE_TRACK_INTERVAL_SECONDS = config("LIVE_TRACK_INTERVAL_SECONDS", default=5, cast=int)
LIVE_TRACK_LATEST_TTL_SECONDS = config("LIVE_TRACK_LATEST_TTL_SECONDS", default=600, cast=int)

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [config("REDIS_URL", default="redis://127.0.0.1:6379/1")],
        },
    },
}

USE_S3_MEDIA = config("USE_S3_MEDIA", default=False, cast=bool)
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="")
AWS_S3_CUSTOM_DOMAIN = config("AWS_S3_CUSTOM_DOMAIN", default="")
AWS_S3_MEDIA_PREFIX = config("AWS_S3_MEDIA_PREFIX", default="media")
AWS_QUERYSTRING_AUTH = config("AWS_QUERYSTRING_AUTH", default=False, cast=bool)
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_S3_SIGNATURE_VERSION = "s3v4"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

if USE_S3_MEDIA:
    if not AWS_STORAGE_BUCKET_NAME:
        raise ValueError("AWS_STORAGE_BUCKET_NAME is required when USE_S3_MEDIA=True.")
    STORAGES["default"] = {
        "BACKEND": "config.storage_backends.MediaS3Storage",
    }
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN.rstrip('/')}/"

CELERY_BEAT_SCHEDULE = {
    "billing-enforce-subscription-lifecycle": {
        "task": "apps.billing.tasks.enforce_subscription_lifecycle_task",
        "schedule": crontab(minute=5, hour=0),
    },
    "billing-send-subscription-expiry-reminders": {
        "task": "apps.billing.tasks.send_subscription_expiry_reminders_task",
        "schedule": crontab(minute=15, hour=9),
    },
}

if AI_AUTOSYNC_ENABLED:
    CELERY_BEAT_SCHEDULE["company-admin-ai-full-sync"] = {
        "task": "company_admin.sync_all_companies_ai_knowledge",
        "schedule": crontab(minute=f"*/{max(1, AI_AUTOSYNC_INTERVAL_MINUTES)}"),
    }
