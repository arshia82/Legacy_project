# users/models.py

import hashlib
import secrets
import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)


# ============================================================
# HELPER FUNCTIONS (Must be at module level for migrations)
# ============================================================

def verification_document_path(instance, filename):
    """Generate upload path for verification documents."""
    ext = filename.split(".")[-1]
    req_id = getattr(instance, "verification_request_id", "temp")
    return f"verifications/{req_id}/{uuid.uuid4().hex}.{ext}"


# ============================================================
# USER MANAGER
# ============================================================

class UserManager(BaseUserManager):
    """Custom manager for User model."""

    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Phone number is required")
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")
        return self.create_user(phone, password, **extra_fields)


# ============================================================
# USER MODEL
# ============================================================

class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model using phone as primary identifier."""

    ROLE_CHOICES = [
        ("athlete", "Athlete"),
        ("coach", "Coach"),
        ("admin", "Admin"),
    ]

    phone = models.CharField(max_length=15, unique=True, db_index=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="athlete")
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()
    USERNAME_FIELD = "phone"

    class Meta:
        db_table = "users_user"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.phone} ({self.role})"


# ============================================================
# OTP MODELS
# ============================================================

class OTP(models.Model):
    """One-Time Password for authentication."""

    phone = models.CharField(max_length=15, db_index=True)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "users_otp"
        verbose_name = "OTP"
        verbose_name_plural = "OTPs"
        ordering = ["-created_at"]

    @classmethod
    def generate_code(cls):
        """Generate a 6-digit OTP code."""
        return "".join(str(secrets.randbelow(10)) for _ in range(6))

    @classmethod
    def hash_code(cls, code):
        """Hash OTP code using SHA-256."""
        return hashlib.sha256(code.encode()).hexdigest()

    def verify_code(self, code):
        """Verify if provided code matches stored hash."""
        if self.is_used or timezone.now() > self.expires_at:
            return False
        return secrets.compare_digest(self.code_hash, self.hash_code(code))


class OTPRateLimit(models.Model):
    """Rate limiting for OTP requests."""

    phone = models.CharField(max_length=15, db_index=True)
    ip_address = models.GenericIPAddressField(db_index=True)
    request_count = models.PositiveIntegerField(default=0)
    daily_count = models.PositiveIntegerField(default=0)
    daily_date = models.DateField(null=True, blank=True)
    is_blocked = models.BooleanField(default=False)
    blocked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users_otp_ratelimit"
        unique_together = ("phone", "ip_address")
        verbose_name = "OTP Rate Limit"
        verbose_name_plural = "OTP Rate Limits"


# ============================================================
# COACH VERIFICATION MODELS
# ============================================================

class CoachVerificationRequest(models.Model):
    """Coach verification request for platform credibility."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    request_number = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_requests")

    coach_message = models.TextField(blank=True, help_text="Message from coach about their qualifications")
    specializations = models.JSONField(default=list, blank=True, help_text="List of coaching specializations")
    years_experience = models.PositiveIntegerField(default=0, help_text="Years of coaching experience")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    # ✅ REQUIRED FIELD (already discussed)
    is_active = models.BooleanField(
        default=True,
        help_text="Only one active verification request is allowed per coach",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users_coach_verification_request"
        verbose_name = "Coach Verification Request"
        verbose_name_plural = "Coach Verification Requests"
        ordering = ["-created_at"]
        # ✅ REQUIRED CONSTRAINT (fixes tests 15 & 29)
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_active=True),
                name="unique_active_verification_per_coach",
            )
        ]

    def save(self, *args, **kwargs):
        """Generate request number on first save."""
        if not self.request_number:
            self.request_number = f"VR-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def can_submit(self):
        """
        Check if request can be submitted.

        Returns:
            Tuple of (can_submit: bool, error_message: str or None)
        """
        if self.status != self.Status.DRAFT:
            return False, "Only draft requests can be submitted"

        if not self.documents.exists():
            return False, "At least one document must be uploaded before submission"

        return True, None

    def submit(self):
        """
        Submit this request for review.
        Added for test compatibility: delegates to service.

        Raises:
            ValidationError: If cannot submit
        """
        from users.services.verification_service import verification_service
        return verification_service.submit_request(self)

    def __str__(self):
        return f"{self.request_number} - {self.user.phone} ({self.status})"


class VerificationDocument(models.Model):
    """Documents uploaded for coach verification."""

    class DocumentType(models.TextChoices):
        ID_CARD = "id_card", "ID Card"
        CERTIFICATE = "certificate", "Certificate"
        LICENSE = "license", "License"
        OTHER = "other", "Other"

    verification_request = models.ForeignKey(
        CoachVerificationRequest,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    file = models.FileField(
        upload_to=verification_document_path,
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png", "webp"])],
    )
    original_filename = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users_verification_document"
        verbose_name = "Verification Document"
        verbose_name_plural = "Verification Documents"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.document_type} for {self.verification_request.request_number}"


class VerificationStatusLog(models.Model):
    """Audit log for verification status changes."""

    verification_request = models.ForeignKey(
        CoachVerificationRequest,
        on_delete=models.CASCADE,
        related_name="status_logs",
    )
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users_verification_status_log"
        verbose_name = "Verification Status Log"
        verbose_name_plural = "Verification Status Logs"
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.verification_request.request_number}: {self.from_status} → {self.to_status}"