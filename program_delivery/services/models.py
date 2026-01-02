from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class ProgramPreset(models.Model):
    coach = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)