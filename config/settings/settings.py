INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third‑party
    "rest_framework",

    # Local apps
    "users.apps.UsersConfig",   # ✅ ADD THIS
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}
KAVENEGAR_API_KEY = "6B78587A63766E58546B554549305A71685276414E5950506D687454776B43624744666C34647A6D3042593D"
KAVENEGAR_SENDER = "2000660110"