from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class AdminAction(models.Model):
    admin = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    target_id = models.IntegerField()
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)