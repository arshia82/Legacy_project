# users/admin.py

from django.contrib import admin
from users.models import (
    User,
    OTP,
    OTPRateLimit,
    CoachVerificationRequest,
    VerificationDocument,
    VerificationStatusLog,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("phone", "role", "is_verified", "is_active")
    search_fields = ("phone",)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("phone", "created_at", "expires_at", "is_used")
    search_fields = ("phone",)


@admin.register(OTPRateLimit)
class OTPRateLimitAdmin(admin.ModelAdmin):
    # ✅ REMOVED daily_count (no longer exists)
    list_display = ("phone", "ip_address", "request_count", "is_blocked")
    search_fields = ("phone", "ip_address")


@admin.register(CoachVerificationRequest)
class CoachVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ("request_number", "user", "status", "created_at")
    search_fields = ("request_number", "user__phone")
    list_filter = ("status",)


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ("verification_request", "document_type", "uploaded_at")


@admin.register(VerificationStatusLog)
class VerificationStatusLogAdmin(admin.ModelAdmin):
    list_display = (
        "verification_request",
        "from_status",
        "to_status",
        "changed_at",
    )