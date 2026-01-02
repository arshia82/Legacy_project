import random
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager

class OTP(models.Model):
    phone_number = models.CharField(max_length=15)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)

    def is_expired(self):
        return timezone.now() > self.expires_at

    @staticmethod
    def generate_code():
        return f"{random.randint(100000, 999999)}"

    @classmethod
    def create_otp(cls, phone_number):
        code = cls.generate_code()
        return cls.objects.create(
            phone_number=phone_number,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=5)
        )
    
import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta


class OTP(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=15)
    code = models.CharField(max_length=6)
    attempts = models.PositiveSmallIntegerField(default=0)

    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.expires_at

    @staticmethod
    def expiry_time():
        return timezone.now() + timedelta(minutes=2)
class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ("athlete", "Athlete"),
        ("coach", "Coach"),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=15, unique=True)

    # ✅ VERIFICATION (NO SLA)
    is_coach_verified = models.BooleanField(default=False)
    coach_verified_at = models.DateTimeField(null=True, blank=True)

    phone_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
from django.db import models
from django.conf import settings


class CoachVerificationRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    coach = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verification_request",
    )

    # Documents / info
    full_name = models.CharField(max_length=255)
    national_id = models.CharField(max_length=10)
    certificate_image = models.ImageField(upload_to="coach_verification/")
    profile_photo = models.ImageField(upload_to="coach_profiles/")

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
    )

    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.coach.phone_number} - {self.status}"