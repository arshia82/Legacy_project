# config/settings/dev.py
"""
Development settings for MY FITA
Local development ONLY – never use in production
Iran‑aware, marketplace‑ready, privacy‑first
"""

from .base import *
from pathlib import Path
import os

# --------------------------------------------------
# CORE
# --------------------------------------------------

DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# --------------------------------------------------
# DATABASE (LOCAL DEV)
# --------------------------------------------------
# SQLite is fine for dev; Postgres will be used later
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# --------------------------------------------------
# APPS
# --------------------------------------------------

INSTALLED_APPS += [
    # Django REST
    "rest_framework",

    # Local domain apps
    "users.apps.UsersConfig",
]

# --------------------------------------------------
# AUTH / USER MODEL
# --------------------------------------------------

# Use custom user model early to avoid future migration pain
AUTH_USER_MODEL = "users.User"

# Faster hashing for local dev
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# --------------------------------------------------
# REST FRAMEWORK (DEV FRIENDLY)
# --------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

# --------------------------------------------------
# EMAIL (DEV)
# --------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# --------------------------------------------------
# FILES / MEDIA (IMPORTANT FOR PHOTO SAFETY)
# --------------------------------------------------

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# NEVER serve sensitive photos publicly in prod
# In dev we allow local testing
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# --------------------------------------------------
# CACHING (LOCAL)
# --------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "myfita-dev-cache",
    }
}

# --------------------------------------------------
# INTERNATIONALIZATION (IRAN‑READY)
# --------------------------------------------------

LANGUAGE_CODE = "fa-ir"

TIME_ZONE = "Asia/Tehran"

USE_I18N = True
USE_L10N = True
USE_TZ = True

# --------------------------------------------------
# SECURITY (DEV ONLY)
# --------------------------------------------------

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# --------------------------------------------------
# LOGGING (VERBOSE FOR DEBUGGING PAYMENTS / OTP)
# --------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
}

# --------------------------------------------------
# MY FITA DOMAIN FLAGS (DEV)
# --------------------------------------------------

# Coach verification SLA is PROCESS‑BASED, not timer‑based
COACH_VERIFICATION_SLA_HOURS = 12

# Commission – mirrors business plan
PLATFORM_COMMISSION_PERCENT = 12

# Payout constraints (used later)
ONLY_VERIFIED_COACH_CAN_WITHDRAW = True

# --------------------------------------------------
# OTP / SMS (DEV MODE)
# --------------------------------------------------
# Real Kavenegar key lives in prod env only
SMS_BACKEND = "console"  # console | kavenegar