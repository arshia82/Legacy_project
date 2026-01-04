from django.contrib import admin
from .models import (
    User,
    OTP,
    OTPRateLimit,
    CoachVerificationRequest,
    VerificationDocument,
    VerificationStatusLog,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "phone",
        "role",
        "is_verified",
        "commission_rate",
        "is_active",
    )
    list_editable = ("commission_rate",)
    search_fields = ("phone",)
    list_filter = ("role", "is_verified", "is_active")
    ordering = ("-id",)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("phone", "created_at", "expires_at", "is_used")
    search_fields = ("phone",)
    ordering = ("-created_at",)


@admin.register(OTPRateLimit)
class OTPRateLimitAdmin(admin.ModelAdmin):
    list_display = ("phone", "ip_address", "request_count", "is_blocked")
    search_fields = ("phone", "ip_address")
    ordering = ("-request_count",)


@admin.register(CoachVerificationRequest)
class CoachVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ("request_number", "user", "status", "created_at")
    search_fields = ("request_number", "user__phone")
    list_filter = ("status",)
    ordering = ("-created_at",)


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ("verification_request", "document_type", "uploaded_at")
    ordering = ("-uploaded_at",)


@admin.register(VerificationStatusLog)
class VerificationStatusLogAdmin(admin.ModelAdmin):
    list_display = (
        "verification_request",
        "from_status",
        "to_status",
        "changed_at",
    )
    ordering = ("-changed_at",)