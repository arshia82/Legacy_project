import os
import sys
from pathlib import Path

# Add project root to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Try to import base settings (ignore errors to prevent crash)
try:
    from config.settings.base import *
except ImportError:
    pass

# --- AUDIT OVERRIDES ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'myfita',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Ensure we have a secret key
if not locals().get('SECRET_KEY'):
    SECRET_KEY = 'audit-override-secret-key-xyz'

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Email backend that doesn't send real emails
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
