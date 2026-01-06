# core/settings.py
from pathlib import Path
from datetime import timedelta
import os
import sys
from dotenv import load_dotenv

# =============================================================================
# BASE DIR & ENV
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# =============================================================================
# SECURITY
# =============================================================================

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY is not set")

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS", "127.0.0.1,localhost"
).split(",")

# =============================================================================
# APPLICATIONS
# =============================================================================

INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    'drf_spectacular',  # Already exists

    # Local apps (relative to backend/)
    "users.apps.UsersConfig",
    "billing.apps.BillingConfig",
    "program_delivery",
    "programs.apps.ProgramsConfig",  # ← ADD .apps.ProgramsConfig HERE (this is the fix)

    #"programs",
    "program_presets",
    
    # --- ADDED: New apps for matching and search ---
    "matching",
    "search",
    # -----------------------------------------------
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
]

# =============================================================================
# AUTH
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
# DATABASE — POSTGRESQL
# =============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "myfita_db"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 600,
        "ATOMIC_REQUESTS": True,
        "OPTIONS": {"connect_timeout": 10},
    }
}

if not DATABASES["default"]["PASSWORD"]:
    raise RuntimeError("POSTGRES_PASSWORD is not set")

# =============================================================================
# I18N
# =============================================================================

LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC & MEDIA
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
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    
    # --- ADDED: API documentation and pagination ---
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # -----------------------------------------------
}

# =============================================================================
# JWT
# =============================================================================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# =============================================================================
# TEST MODE
# =============================================================================

TESTING = "test" in sys.argv

# =============================================================================
# ADDED: DRF SPECTACULAR (API DOCUMENTATION)
# =============================================================================

SPECTACULAR_SETTINGS = {
    "TITLE": "MY FITA API",
    "DESCRIPTION": """
    Persian web marketplace connecting verified coaches with athletes across Iran.
    
    **Business Plan Reference:**
    - Platform commission on program sales (average 12% of GMV)
    - B2B club packages (800,000 Toman per 90 users)
    - AI-powered coach-athlete matching
    - Secure messaging and call masking
    - Payout workflows via Iranian PSPs
    
    **Core Features:**
    - Coach & Athlete profiles
    - Search & filter coaches
    - Program purchase & delivery (PDF generation)
    - Billing & commission management
    - AI matching service
    - Admin verification workflow (12-hour target)
    """,
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/",
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
    },
    "SERVERS": [
        {"url": "http://127.0.0.1:8000", "description": "Development server"},
        {"url": "https://api.myfita.ir", "description": "Production server"},
    ],
}

# =============================================================================
# ADDED: CACHING (For search and matching services)
# =============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
        }
    }
}

# Optional: Redis cache for production (uncomment when ready)
# REDIS_URL = os.getenv("REDIS_URL", "")
# if REDIS_URL:
#     CACHES = {
#         "default": {
#             "BACKEND": "django_redis.cache.RedisCache",
#             "LOCATION": REDIS_URL,
#             "OPTIONS": {
#                 "CLIENT_CLASS": "django_redis.client.DefaultClient",
#             }
#         }
#     }

# =============================================================================
# ADDED: LOGGING (For debugging and monitoring)
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "myfita.log",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "matching": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "search": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "billing": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

# =============================================================================
# ADDED: MATCHING SERVICE CONFIGURATION
# =============================================================================

# BP: "MY FITA's AI recommends a shortlist of matched coaches"
MATCHING_CONFIG = {
    # Minimum profile completion for matching
    "MIN_ATHLETE_COMPLETION": 70,  # 70% profile completion required
    "MIN_COACH_COMPLETION": 80,    # 80% profile completion required
    
    # Match scoring weights (must sum to 100)
    "SCORE_WEIGHTS": {
        "goal_specialization_match": 35,  # Primary alignment
        "experience_level_match": 15,
        "location_match": 15,
        "price_fit": 15,
        "coach_rating": 10,
        "availability": 5,
        "gender_preference": 5,
    },
    
    # Cache settings
    "CACHE_MATCH_RESULTS": True,
    "CACHE_TTL_SECONDS": 3600,  # 1 hour
    
    # Result limits
    "DEFAULT_MATCH_LIMIT": 20,
    "MAX_MATCH_LIMIT": 50,
}

# =============================================================================
# ADDED: SEARCH SERVICE CONFIGURATION
# =============================================================================

# BP: "coach athlete profiles, search filter"
# BP: "capture high-intent organic search traffic"
SEARCH_CONFIG = {
    # Search result limits
    "DEFAULT_PAGE_SIZE": 20,
    "MAX_PAGE_SIZE": 50,
    
    # Text search
    "MIN_QUERY_LENGTH": 2,
    "MAX_QUERY_LENGTH": 255,
    
    # Autocomplete
    "AUTOCOMPLETE_LIMIT": 10,
    
    # Popular searches
    "POPULAR_SEARCH_MIN_COUNT": 5,  # Minimum searches to be "popular"
    
    # Saved searches per user
    "MAX_SAVED_SEARCHES_PER_USER": 20,
}

# =============================================================================
# ADDED: BILLING & COMMISSION CONFIGURATION
# =============================================================================

# BP: "platform commission on program sales (average 12% of GMV)"
# BP: "payout workflows via Iranian PSPs"
BILLING_CONFIG = {
    # Commission rates
    "DEFAULT_COMMISSION_RATE": 0.12,  # 12% platform take rate
    "MIN_COMMISSION_RATE": 0.08,      # 8% minimum
    "MAX_COMMISSION_RATE": 0.20,      # 20% maximum
    
    # Payout settings
    "MIN_PAYOUT_AMOUNT": 100000,      # 100,000 Toman minimum
    "PAYOUT_FREQUENCY_DAYS": 7,       # Weekly payouts
    "PAYOUT_PROCESSING_HOURS": 48,    # 48-hour processing time
    
    # Trust token settings (anti-disintermediation)
    "TOKEN_EXPIRY_HOURS": 72,         # 3 days
    "TOKEN_MAX_USE_COUNT": 1,         # Single use
    
    # B2B club packages
    "B2B_PACKAGE_BASE_PRICE": 800000,  # 800,000 Toman per 90 users
    "B2B_PACKAGE_BASE_USERS": 90,
}

# =============================================================================
# ADDED: ADMIN VERIFICATION WORKFLOW
# =============================================================================

# BP: "admin verification workflow aims for verified status within 12 hours"
VERIFICATION_CONFIG = {
    "TARGET_VERIFICATION_HOURS": 12,  # 12-hour target
    "AUTO_REJECT_AFTER_DAYS": 30,     # Auto-reject after 30 days
    "REQUIRED_DOCUMENTS": [
        "national_id",
        "certification",
        "profile_photo"
    ],
    "ALLOWED_FILE_TYPES": ["pdf", "jpg", "jpeg", "png", "webp"],
    "MAX_FILE_SIZE_MB": 5,
}

# =============================================================================
# ADDED: SECURITY ENHANCEMENTS
# =============================================================================

# Session security
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# CSRF security
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

# Additional security headers (production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"

# =============================================================================
# ADDED: RATE LIMITING (For API endpoints)
# =============================================================================

REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = [
    "rest_framework.throttling.AnonRateThrottle",
    "rest_framework.throttling.UserRateThrottle",
]

REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "anon": os.getenv("RATE_ANON", "100/hour"),
    "user": os.getenv("RATE_USER", "1000/hour"),
    "search": "60/minute",  # Search endpoint specific
}

# =============================================================================
# ADDED: FILE UPLOAD SETTINGS
# =============================================================================

# BP: "program purchase delivery (PDF)"
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# Allowed file extensions for program PDFs
ALLOWED_PROGRAM_FILE_TYPES = ["pdf"]
MAX_PROGRAM_FILE_SIZE_MB = 10

# Allowed file extensions for verification documents
ALLOWED_VERIFICATION_FILE_TYPES = ["pdf", "jpg", "jpeg", "png", "webp"]
MAX_VERIFICATION_FILE_SIZE_MB = 5

# =============================================================================
# END OF ADDITIONS
# =============================================================================