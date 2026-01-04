# core/settings.py
"""
MY-FITA Platform Settings
Production-ready configuration with PostgreSQL
"""

from pathlib import Path
from datetime import timedelta
import os
# core/settings.py

from pathlib import Path
from datetime import timedelta
import os
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
# ✅ خواندن فایل .env
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# ✅ بارگذاری متغیرهای .env
load_dotenv(BASE_DIR / '.env')

# حالا می‌تونی از os.getenv استفاده کنی:
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "fallback-key")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# ... ادامه settings
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# SECURITY
# =============================================================================

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-key-change-in-production"
)

DEBUG = os.getenv("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# =============================================================================
# APPLICATIONS
# =============================================================================

INSTALLED_APPS = [
    "myfita.apps.backend.users.apps.UsersConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "program_delivery",
    "programs",
    "program_presets",
    "billing",
]

# =============================================================================
# MIDDLEWARE
# =============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Rate limiting (optional - uncomment when Redis is ready)
    # "users.middleware.rate_limit.RateLimitMiddleware",
]

# =============================================================================
# AUTHENTICATION
# =============================================================================

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =============================================================================
# URLS & TEMPLATES
# =============================================================================

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

# =============================================================================
# DATABASE — POSTGRESQL (Changed from SQLite)
# =============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "myfita_db"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "ATOMIC_REQUESTS": True,  # Prevents race conditions
        "CONN_MAX_AGE": 600,  # Connection pooling
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# Test database configuration
if "test" in os.sys.argv:
    DATABASES["default"]["TEST"] = {
        "NAME": "test_myfita_db",
    }

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# REST FRAMEWORK
# =============================================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "otp_send": "3/hour",
        "otp_verify": "10/hour",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}

# =============================================================================
# JWT SETTINGS
# =============================================================================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# =============================================================================
# OTP CONFIGURATION
# =============================================================================

OTP_CONFIG = {
    "TTL_SECONDS": 300,
    "MAX_ATTEMPTS": 5,
    "MAX_SENDS_PER_HOUR": 3,
    "COOLDOWN_SECONDS": 60,
    "CODE_LENGTH": 6,
}

# =============================================================================
# KAVENEGAR SMS
# =============================================================================

KAVENEGAR = {
    "API_KEY": os.getenv(
        "KAVENEGAR_API_KEY",
        "6B78587A63766E58546B554549305A71685276414E5950506D687454776B43624744666C34647A6D3042593D"
    ),
    "SENDER": "2000660110",
}

# =============================================================================
# MY-FITA BUSINESS SETTINGS (from Business Plan)
# =============================================================================

MYFITA = {
    "PLATFORM_COMMISSION_PERCENT": 12,  # Business Plan: 12% take rate
    "VERIFICATION_SLA_HOURS": 12,  # Business Plan: 12-hour verification SLA
    "ALLOW_UNVERIFIED_COACH_VISIBILITY": False,  # Business Plan: Trust-first
    "COACH_WITHDRAWAL_REQUIRES_VERIFICATION": True,
    "AI_ENABLED": False,  # Post-MVP feature
}

VERIFICATION_SETTINGS = {
    "MAX_FILES_PER_REQUEST": 10,
    "MAX_FILE_SIZE_MB": 5,
    "ALLOWED_EXTENSIONS": ["pdf", "jpg", "jpeg", "png", "webp"],
}

# =============================================================================
# REDIS CONFIGURATION
# =============================================================================

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

REDIS_CONFIG = {
    "host": REDIS_HOST,
    "port": REDIS_PORT,
    "db": REDIS_DB,
    "decode_responses": True,
    "socket_connect_timeout": 2,
    "socket_timeout": 2,
    "retry_on_timeout": True,
    "health_check_interval": 30,
}

# Use Django cache as fallback when Redis is not available
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# =============================================================================
# RATE LIMITING
# =============================================================================

RATE_LIMITS = {
    "otp_request": {"limit": 5, "window": 3600},      # 5 per hour
    "otp_verify": {"limit": 10, "window": 600},       # 10 per 10 min
    "login": {"limit": 10, "window": 900},            # 10 per 15 min
    "api_global": {"limit": 100, "window": 60},       # 100 per minute
    "api_user": {"limit": 60, "window": 60},          # 60 per minute
}





# ✅ ADD THIS
MIGRATION_MODULES = {
    "users": "users.migrations",
}
# =============================================================================
# TESTING MODE
# =============================================================================

TESTING = "test" in os.sys.argv