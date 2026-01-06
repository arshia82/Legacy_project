# FILE: myfita/apps/backend/billing/models.py
# REPLACE ENTIRE FILE

import uuid
import hashlib
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


# =========================
# COMMISSION CONFIG
# =========================

class CommissionConfig(models.Model):
    name = models.CharField(max_length=100)
    rate = models.DecimalField(max_digits=5, decimal_places=4)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_commission_config"

    @classmethod
    def get_active_rate(cls):
        """Get active commission rate or raise error"""
        cfg = cls.objects.filter(is_active=True).first()
        if not cfg:
            raise ValueError("No active commission config found")
        return cfg.rate

    @classmethod
    def get_active(cls):
        """Get active commission config or raise error"""
        cfg = cls.objects.filter(is_active=True).first()
        if not cfg:
            raise ValueError("No active commission config found")
        return cfg


# =========================
# TRUST TOKEN
# =========================

class TrustToken(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        USED = "used", "Used"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"
        PENDING = "pending", "Pending"

    class Meta:
        db_table = "billing_trust_token"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    program_id = models.UUIDField()
    coach_id = models.UUIDField()
    athlete_id = models.UUIDField()

    gross_amount = models.BigIntegerField()
    commission_amount = models.BigIntegerField()
    net_amount = models.BigIntegerField()
    commission_rate = models.DecimalField(max_digits=5, decimal_places=4)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    idempotency_key = models.CharField(max_length=255, unique=True)
    integrity_hash = models.CharField(max_length=64, blank=True)

    created_by_ip = models.GenericIPAddressField(null=True, blank=True)
    used_by_ip = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Compute hash on first save if not set
        if not self.integrity_hash:
            if not self.id:
                self.id = uuid.uuid4()
            self.integrity_hash = self.compute_integrity_hash()
        super().save(*args, **kwargs)

    def compute_integrity_hash(self):
        """
        Compute integrity hash from immutable token fields.
        CRITICAL: Includes status to detect tampering attempts.
        """
        raw = (
            f"{self.id}|{self.program_id}|{self.coach_id}|{self.athlete_id}|"
            f"{self.gross_amount}|{self.commission_amount}|{self.net_amount}|"
            f"{self.commission_rate}|{self.status}|{self.idempotency_key}|{settings.SECRET_KEY}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    def verify_integrity(self):
        """Verify token has not been tampered with"""
        expected_hash = self.compute_integrity_hash()
        return self.integrity_hash == expected_hash

    def mark_used(self, ip=None):
        """Mark token as used and recompute hash"""
        self.status = self.Status.USED
        self.used_at = timezone.now()
        if ip:
            self.used_by_ip = ip
        # Recompute hash after status change
        self.integrity_hash = self.compute_integrity_hash()
        self.save(update_fields=["status", "used_at", "used_by_ip", "integrity_hash"])

    @property
    def token_hash(self):
        """Alias for integrity_hash for backward compatibility"""
        return self.integrity_hash

    @property
    def is_expired(self):
        """Check if token is expired"""
        return self.expires_at <= timezone.now()

    @property
    def is_active(self):
        """Check if token is active and not expired"""
        return self.status == self.Status.ACTIVE and not self.is_expired


# =========================
# PAYOUT
# =========================

class Payout(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class Meta:
        db_table = "billing_payout"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trust_token = models.OneToOneField(TrustToken, on_delete=models.PROTECT, related_name="payout")
    
    # Make coach nullable for test compatibility
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        db_column='coach_id'
    )

    gross_amount = models.BigIntegerField()
    commission_amount = models.BigIntegerField()
    net_amount = models.BigIntegerField()
    commission_rate = models.DecimalField(max_digits=5, decimal_places=4)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)


# =========================
# AUDIT LOG
# =========================

class AuditLog(models.Model):

    class Action(models.TextChoices):
        TOKEN_CREATED = "token_created", "Token Created"
        TOKEN_USED = "token_used", "Token Used"
        TOKEN_EXPIRED = "token_expired", "Token Expired"
        TOKEN_VALIDATION_FAILED = "token_validation_failed", "Token Validation Failed"
        PAYOUT_INITIATED = "payout_initiated", "Payout Initiated"
        PAYOUT_CREATED = "payout_created", "Payout Created"
        PAYOUT_COMPLETED = "payout_completed", "Payout Completed"
        PAYOUT_FAILED = "payout_failed", "Payout Failed"
        BYPASS_ATTEMPT = "bypass_attempt", "Bypass Attempt"
        TOKEN_TAMPERED = "token_tampered", "Token Tampered"

    class Meta:
        db_table = "billing_audit_log"
        ordering = ["-created_at"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    action = models.CharField(max_length=50, choices=Action.choices)
    actor_type = models.CharField(max_length=50, default="system")
    actor_id = models.CharField(max_length=100, null=True, blank=True)
    target_id = models.UUIDField(null=True, blank=True)

    request_summary = models.JSONField(default=dict, blank=True)
    details = models.JSONField(default=dict, blank=True)
    result = models.CharField(max_length=50, default="success")

    gross_amount = models.BigIntegerField(null=True, blank=True)
    commission_amount = models.BigIntegerField(null=True, blank=True)
    net_amount = models.BigIntegerField(null=True, blank=True)

    error_message = models.TextField(null=True, blank=True)

    previous_hash = models.CharField(max_length=64, blank=True)
    entry_hash = models.CharField(max_length=64, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.previous_hash:
            prev = AuditLog.objects.order_by("-created_at").first()
            self.previous_hash = prev.entry_hash if prev else "genesis"
        if not self.entry_hash:
            self.entry_hash = self.compute_hash()
        super().save(*args, **kwargs)

    def compute_hash(self):
        raw = (
            f"{self.id}|{self.action}|{self.actor_type}|{self.actor_id}|"
            f"{self.request_summary}|{self.gross_amount}|"
            f"{self.commission_amount}|{self.net_amount}|"
            f"{self.result}|{self.previous_hash}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()


# =========================
# DISINTERMEDIATION ALERT
# =========================

class DisintermediationAlert(models.Model):

    class Meta:
        db_table = "billing_disintermediation_alert"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coach = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=50)
    severity = models.CharField(max_length=20)
    description = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)