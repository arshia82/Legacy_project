from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"

    # ✅ FULL PYTHON PATH
    name = "myfita.apps.backend.users"

    # ✅ KEEP DB TABLES AS `users_*`
    label = "users"