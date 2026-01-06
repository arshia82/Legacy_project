# FILE: myfita/apps/backend/matching/apps.py

from django.apps import AppConfig


class MatchingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'matching'
    verbose_name = 'Coach-Athlete Matching'