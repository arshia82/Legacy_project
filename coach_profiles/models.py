from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class CoachProfile(models.Model):
    """
    Public-facing coach profile.
    Sensitive data handled via permissions.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    expertise = models.CharField(max_length=255)
    is_visible = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class CoachMedia(models.Model):
    """
    Private media (photos, badges).
    NEVER public.
    """
    profile = models.ForeignKey(CoachProfile, on_delete=models.CASCADE)
    file = models.FileField(upload_to="coach_media/")
    is_deleted = models.BooleanField(default=False)

    uploaded_at = models.DateTimeField(auto_now_add=True)